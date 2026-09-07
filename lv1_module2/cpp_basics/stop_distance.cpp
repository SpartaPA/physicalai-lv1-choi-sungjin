#include <iomanip>
#include <iostream>

int main()
{
    double speed_mps{};
    double friction_coefficient{};

    std::cout << "Speed (m/s): ";
    if (!(std::cin >> speed_mps) || speed_mps < 0.0) {
        std::cerr << "Error: speed must be zero or greater.\n";
        return 1;
    }

    std::cout << "Friction coefficient: ";
    if (!(std::cin >> friction_coefficient) || friction_coefficient <= 0.0) {
        std::cerr << "Error: friction coefficient must be greater than zero.\n";
        return 1;
    }

    constexpr double gravity_mps2 = 9.81;
    const double stopping_distance_m =
        speed_mps * speed_mps /
        (2.0 * friction_coefficient * gravity_mps2);

    std::cout << std::fixed << std::setprecision(3)
              << "Stopping distance: " << stopping_distance_m << " m\n";

    return 0;
}

