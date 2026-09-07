#include "motor.hpp"

#include <iostream>
#include <utility>
// std=c++17 로할거야 알겠냐? 컴파일러에게 컴파일할 때 표준을 c++17 버전으로 할거야 라고 알려주는 옵션이다.
// 컴파일러 옵션은 컴파일러에 대한 설정을 하는 옵션이다. 명령어를 칠 때 옵션을 줄 수 있다.
Motor::Motor(std::string name)
    : name_(std::move(name))
{
}

void Motor::set_rpm(double rpm)
{
    rpm_ = rpm;
}

void Motor::print_status() const
{
    std::cout << name_ << " motor speed: " << rpm_ << " rpm\n";
}
