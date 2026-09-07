#pragma once

#include <iostream>
#include <string>
#include <utility>

// 모든 센서가 공통으로 따라야 하는 추상 기반 클래스입니다.
// read()가 순수 가상 함수이므로 Sensor 객체 자체는 만들 수 없습니다.
class Sensor {
public:
    explicit Sensor(std::string name) : name_(std::move(name)) {
        std::cout << "[create] Sensor base: " << name_ << '\n';
    }

#ifdef SENSOR_DEMO_NON_VIRTUAL_DESTRUCTOR
    // 과제 비교 실험 전용입니다. 이 모드에서 기반 클래스 포인터로 파생 객체를
    // 삭제하는 것은 정의되지 않은 동작(undefined behavior)입니다.
    ~Sensor() {
        std::cout << "[destroy] Sensor base (NON-VIRTUAL): " << name_ << '\n';
    }
#else
    // 다형적으로 삭제할 때 Lidar/Imu 소멸자가 먼저 호출되도록 반드시 virtual로 둡니다.
    virtual ~Sensor() {
        std::cout << "[destroy] Sensor base: " << name_ << '\n';
    }
#endif

    Sensor(const Sensor&) = delete;
    Sensor& operator=(const Sensor&) = delete;
    Sensor(Sensor&&) = default;
    Sensor& operator=(Sensor&&) = default;

    virtual double read() const = 0;

    const std::string& name() const {
        return name_;
    }

private:
    std::string name_;
};
