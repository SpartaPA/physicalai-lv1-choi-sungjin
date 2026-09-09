"""새 커널로 노트북 3개를 실행하고 저장된 결과를 검사한다."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import nbformat
from nbclient import NotebookClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def output_text(cell):
    return "\n".join(
        out.get("text", "") if out.output_type == "stream"
        else out.get("data", {}).get("text/plain", "")
        for out in cell.get("outputs", [])
    )


def export_notebook_images(notebook, name):
    images = ROOT / "images"
    images.mkdir(exist_ok=True)
    for index, cell in enumerate(notebook.cells):
        for output in cell.get("outputs", []):
            encoded = output.get("data", {}).get("image/png")
            if encoded:
                (images / f"{name[:2]}_cell{index:02d}.png").write_bytes(base64.b64decode(encoded))


def interpreter_environment():
    return {"executable": sys.executable, "prefix": sys.prefix,
            "base_prefix": sys.base_prefix}


def normalized_path(path):
    # resolve()는 venv의 python 심볼릭 링크를 시스템 python으로 합쳐 버린다.
    return os.path.normcase(os.path.abspath(path))


def require_venv(environment, label):
    if normalized_path(environment["prefix"]) == normalized_path(environment["base_prefix"]):
        raise RuntimeError(f"{label}이 가상환경 파이썬이 아닙니다: {environment['executable']}")


def inspect_kernel_environment(kernel):
    probe = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
        "import json, sys\n"
        "print('KERNEL_ENV=' + json.dumps({'executable': sys.executable, "
        "'prefix': sys.prefix, 'base_prefix': sys.base_prefix}))"
    )])
    NotebookClient(probe, kernel_name=kernel, timeout=60,
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    for line in output_text(probe.cells[0]).splitlines():
        if line.startswith("KERNEL_ENV="):
            return json.loads(line.removeprefix("KERNEL_ENV="))
    raise RuntimeError("커널의 실제 파이썬 환경을 확인하지 못했습니다")


def require_same_environment(runner, kernel):
    require_venv(runner, "검증 실행기")
    require_venv(kernel, "노트북 커널")
    if normalized_path(runner["prefix"]) != normalized_path(kernel["prefix"]):
        raise RuntimeError(
            "검증 실행기와 노트북 커널의 가상환경이 다릅니다. "
            f"실행기: {runner['executable']}, 커널: {kernel['executable']}. "
            "현재 가상환경에서 README의 ipykernel install 명령을 다시 실행하세요."
        )


def write_receipt(evidence, receipt):
    path = evidence / "notebook_validation.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_order_experiment(kernel):
    source = nbformat.read(ROOT / "notebooks/01_pipeline.ipynb", 4)
    steps = []
    for label, order, expected_error in [
        ("A B C B B C", [5, 6, 7, 6, 6, 7], False),
        ("새 커널에서 C만 실행", [7], True),
    ]:
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_code_cell(source.cells[index].source) for index in order
        ])
        NotebookClient(notebook, kernel_name=kernel, timeout=60,
                       allow_errors=expected_error,
                       resources={"metadata": {"path": str(ROOT)}}).execute()
        records = [{"source": cell.source, "execution_count": cell.execution_count,
                    "outputs": cell.outputs} for cell in notebook.cells]
        if expected_error:
            errors = [out.get("ename") for out in notebook.cells[0].outputs
                      if out.output_type == "error"]
            if errors != ["NameError"]:
                raise RuntimeError(f"C 단독 실행의 예상 오류와 다릅니다: {errors}")
        elif ("최종 count = 1" not in output_text(notebook.cells[2])
              or "최종 count = 3" not in output_text(notebook.cells[5])):
            raise RuntimeError("셀 반복 실행 결과가 예상 count와 다릅니다")
        steps.append({"experiment": label, "cells": records})
    return steps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", default="physicalai-lv1-math")
    args = parser.parse_args()
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    receipt = {"started_at_utc": timestamp, "kernel": args.kernel,
               "runner_python": sys.executable, "runner_environment": interpreter_environment(),
               "pytest_returncode": None, "notebooks": [], "passed": False,
               "status": "running", "stage": "environment"}
    # 조기 실패 때 이전 실행의 passed:true 기록이 남지 않도록 먼저 교체한다.
    write_receipt(evidence, receipt)
    try:
        require_venv(receipt["runner_environment"], "검증 실행기")
        receipt["kernel_environment"] = inspect_kernel_environment(args.kernel)
        require_same_environment(receipt["runner_environment"], receipt["kernel_environment"])
        receipt["stage"] = "pytest"
        write_receipt(evidence, receipt)
        result = subprocess.run([sys.executable, "-m", "pytest", "-v"], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8")
        receipt["pytest_returncode"] = result.returncode
        (evidence / "pytest.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(result.stdout, flush=True)
        result.check_returncode()
        receipt["stage"] = "cell_order_experiment"
        write_receipt(evidence, receipt)
        experiments = {"executed_at_utc": datetime.now(timezone.utc).isoformat(),
                       "kernel": args.kernel, "experiments": run_order_experiment(args.kernel)}
        (evidence / "cell_order_experiment.json").write_text(
            json.dumps(experiments, ensure_ascii=False, indent=2), encoding="utf-8")
        run_notebooks(args.kernel, evidence, receipt)
        receipt["stage"] = "gif"
        with Image.open(ROOT / "demo.gif") as gif:
            receipt["gif"] = {"frames": gif.n_frames, "size": list(gif.size),
                              "bytes": (ROOT / "demo.gif").stat().st_size}
        receipt["passed"] = True
        receipt["status"] = "passed"
        receipt["stage"] = "complete"
    except BaseException as error:
        receipt["passed"] = False
        receipt["status"] = "failed"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error),
                              "stage": receipt["stage"]}
        raise
    finally:
        receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_receipt(evidence, receipt)
    print("노트북 3개 전체 실행 및 저장 결과 검사 통과", flush=True)


def run_notebooks(kernel, evidence, receipt):
    for name in ["01_pipeline.ipynb", "02_interpolation.ipynb", "03_pose_estimation.ipynb"]:
        receipt["stage"] = "notebooks/" + name
        write_receipt(evidence, receipt)
        path = ROOT / "notebooks" / name
        notebook = nbformat.read(path, 4)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.outputs = []
                cell.execution_count = None
        notebook.metadata.kernelspec = {"name": kernel, "language": "python",
                                        "display_name": "Python (pose_lab)"}
        print("Executing", name, flush=True)
        execution_error = None
        try:
            NotebookClient(notebook, kernel_name=kernel, timeout=600,
                           resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
        except Exception as error:
            execution_error = str(error)
        finally:
            nbformat.write(notebook, path)
        code = [cell for cell in notebook.cells if cell.cell_type == "code"]
        text = "\n".join(output_text(cell) for cell in code)
        errors = [out.ename for cell in code for out in cell.outputs if out.output_type == "error"]
        overall = [line.strip() for line in text.splitlines() if "전체 통과:" in line]
        counts = [cell.execution_count for cell in code]
        entry = {
            "file": "notebooks/" + name,
            "code_cells": len(code), "execution_counts_in_order": counts == list(range(1, len(code)+1)),
            "unexecuted": counts.count(None), "errors": errors,
            "pass_count": text.count("[PASS]"), "fail_count": text.count("[FAIL]"),
            "overall_results": overall,
            "png_outputs": sum("image/png" in out.get("data", {}) for cell in code for out in cell.outputs),
            "html_outputs": sum("text/html" in out.get("data", {}) for cell in code for out in cell.outputs),
        }
        entry["passed"] = (execution_error is None and not errors and entry["unexecuted"] == 0
                           and entry["execution_counts_in_order"] and entry["fail_count"] == 0
                           and bool(overall) and all(line.endswith("True") for line in overall))
        if execution_error:
            entry["execution_error"] = execution_error
        receipt["notebooks"].append(entry)
        (evidence / (path.stem + ".txt")).write_text(text, encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        if not entry["passed"]:
            raise RuntimeError(f"노트북 검증 실패: {name}; evidence/notebook_validation.json 확인")
        export_notebook_images(notebook, name)


if __name__ == "__main__":
    main()
