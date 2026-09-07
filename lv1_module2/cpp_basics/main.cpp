#include "motor.hpp"

int main()
{
    Motor left_motor{"left"};
    Motor right_motor{"right"};

    left_motor.set_rpm(120.0);
    right_motor.set_rpm(115.0);

    left_motor.print_status();
    right_motor.print_status();

    return 0;
}

