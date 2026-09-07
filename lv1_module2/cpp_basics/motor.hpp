#pragma once

#include <string>

class Motor
{
public:
    explicit Motor(std::string name);

    void set_rpm(double rpm);
    void print_status() const;

private:
    std::string name_;
    double rpm_{0.0};
};

