#pragma once

#include "sensor.hpp"

#include <iostream>
#include <string>
#include <utility>
#include <vector>

class Lidar final : public Sensor {
public:
    Lidar(std::string name, double distance_m)
        : Sensor(std::move(name)),
          scan_values_{distance_m, distance_m + 0.1, distance_m + 0.2} {
        std::cout << "[create] Lidar: " << this->name() << '\n';
    }

#ifdef SENSOR_DEMO_NON_VIRTUAL_DESTRUCTOR
    ~Lidar() {
#else
    ~Lidar() override {
#endif
        std::cout << "[destroy] Lidar: " << name() << '\n';
    }

    double read() const override {
        const double distance_m = scan_values_.front();
        std::cout << "[read] " << name() << " (Lidar) = "
                  << distance_m << " m\n";
        return distance_m;
    }

private:
    // 파생 클래스에 별도 자원이 있음을 보여 주기 위한 간단한 스캔 데이터입니다.
    std::vector<double> scan_values_;
};
