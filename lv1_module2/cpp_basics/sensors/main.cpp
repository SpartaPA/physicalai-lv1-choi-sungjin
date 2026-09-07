#include "imu.hpp"
#include "lidar.hpp"

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

template <typename T>
T clamp(const T& value, const T& minimum, const T& maximum) {
    return std::max(minimum, std::min(value, maximum));
}

bool has_argument(int argc, char* argv[], const std::string& expected) {
    for (int index = 1; index < argc; ++index) {
        if (argv[index] == expected) {
            return true;
        }
    }
    return false;
}

void demonstrate_polymorphism_and_stl() {
    std::cout << "\n=== 1. Polymorphism with unique_ptr ===\n";

    std::vector<std::unique_ptr<Sensor>> sensors;
    sensors.push_back(std::make_unique<Lidar>("front_lidar", 1.20));
    sensors.push_back(std::make_unique<Imu>("body_imu", 0.35));

    std::unordered_map<std::string, double> latest_measurements;
    for (const auto& sensor : sensors) {
        latest_measurements[sensor->name()] = sensor->read();
    }

    std::cout << "\nLatest measurements (unordered_map)\n";
    for (const auto& [name, value] : latest_measurements) {
        std::cout << "  " << name << " -> " << value << '\n';
    }

    const std::vector<double> distance_log{1.20, 0.49, 0.50, 0.51, 0.10, 0.90};
    const auto near_count = std::count_if(
        distance_log.begin(),
        distance_log.end(),
        [](double distance) { return distance <= 0.35; });

    std::cout << "Records within 0.35 m: " << near_count << '\n';
    std::cout << "Leaving this function destroys vector elements automatically.\n";
}

void demonstrate_clamp_template() {
    std::cout << "\n=== 2. clamp template ===\n";

    const double requested_speed = 3.7;
    const int requested_pixel = 300;

    std::cout << "double speed: " << requested_speed << " -> "
              << clamp(requested_speed, 0.0, 2.0) << '\n';
    std::cout << "int pixel: " << requested_pixel << " -> "
              << clamp(requested_pixel, 0, 255) << '\n';
}

void demonstrate_stack_and_heap_lifetime() {
    std::cout << "\n=== 3. Stack lifetime ===\n";
    {
        Lidar stack_sensor("stack_lidar", 2.40);
        stack_sensor.read();
        std::cout << "End of stack scope -> destructor runs now.\n";
    }

    std::cout << "\n=== 4. Heap lifetime managed by unique_ptr ===\n";
    {
        auto heap_sensor = std::make_unique<Imu>("heap_imu", 0.75);
        heap_sensor->read();
        std::cout << "End of unique_ptr scope -> destructor runs now.\n";
    }
}

void reproduce_memory_leak() {
    std::cout << "\n=== Intentional memory leak (assignment experiment) ===\n";
    std::cout << "The raw pointers below are intentionally not deleted.\n";

    for (int index = 0; index < 3; ++index) {
        Sensor* leaked_sensor = new Lidar(
            "leaked_lidar_" + std::to_string(index),
            1.0 + index);
        leaked_sensor->read();
        // 과제의 ASan 검출 실험을 위해 delete를 일부러 생략합니다.
    }

    std::cout << "Program exit: AddressSanitizer should report the leak.\n";
}

void demonstrate_fixed_memory_management() {
    std::cout << "\n=== Fixed version using make_unique ===\n";

    std::vector<std::unique_ptr<Sensor>> sensors;
    for (int index = 0; index < 3; ++index) {
        sensors.push_back(std::make_unique<Lidar>(
            "managed_lidar_" + std::to_string(index),
            1.0 + index));
    }

    for (const auto& sensor : sensors) {
        sensor->read();
    }

    std::cout << "Program exit: unique_ptr releases every sensor automatically.\n";
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(2);

#ifdef SENSOR_DEMO_NON_VIRTUAL_DESTRUCTOR
    if (!has_argument(argc, argv, "--destructor-demo")) {
        std::cout << "This target is only for the non-virtual destructor experiment.\n"
                  << "Run: ./sensors_no_virtual --destructor-demo\n";
        return 0;
    }

    std::cout << "=== Non-virtual destructor experiment (intentional UB) ===\n";
    std::unique_ptr<Sensor> sensor =
        std::make_unique<Lidar>("destructor_test_lidar", 1.50);
    sensor->read();
    std::cout << "Deleting a Lidar through Sensor* now.\n";
    sensor.reset();
    return 0;
#else
    if (has_argument(argc, argv, "--leak")) {
        reproduce_memory_leak();
        return 0;
    }

    if (has_argument(argc, argv, "--fixed")) {
        demonstrate_fixed_memory_management();
        return 0;
    }

    std::cout << "Modern C++ sensor hierarchy demo\n";
    demonstrate_polymorphism_and_stl();
    demonstrate_clamp_template();
    demonstrate_stack_and_heap_lifetime();

    std::cout << "\nAll normal demonstrations completed.\n";
    return 0;
#endif
}
