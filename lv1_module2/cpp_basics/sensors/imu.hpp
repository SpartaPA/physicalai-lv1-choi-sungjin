#pragma once

#include "sensor.hpp"

#include <array>
#include <iostream>
#include <string>
#include <utility>

class Imu final : public Sensor {
public:
    Imu(std::string name, double angular_velocity_rad_s)
        : Sensor(std::move(name)),
          angular_velocity_{0.0, 0.0, angular_velocity_rad_s} {
        std::cout << "[create] Imu: " << this->name() << '\n';
    }

#ifdef SENSOR_DEMO_NON_VIRTUAL_DESTRUCTOR
    ~Imu() {
#else
    ~Imu() override {
#endif
        std::cout << "[destroy] Imu: " << name() << '\n';
    }

    double read() const override {
        const double yaw_rate = angular_velocity_[2];
        std::cout << "[read] " << name() << " (Imu yaw rate) = "
                  << yaw_rate << " rad/s\n";
        return yaw_rate;
    }

private:
    std::array<double, 3> angular_velocity_;
};
