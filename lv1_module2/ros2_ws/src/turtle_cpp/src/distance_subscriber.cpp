#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32.hpp"

class DistanceSubscriber : public rclcpp::Node
{
public:
  DistanceSubscriber()
  : Node("cpp_distance_subscriber")
  {
    const auto distance_topic =
      declare_parameter<std::string>("distance_topic", "/turtle_distance");

    subscription_ = create_subscription<std_msgs::msg::Float32>(
      distance_topic,
      10,
      [this](const std_msgs::msg::Float32::SharedPtr message) {
        RCLCPP_INFO(get_logger(), "C++ received distance: %.3f m", message->data);
      });

    RCLCPP_INFO(get_logger(), "C++ subscriber listening on %s", distance_topic.c_str());
  }

private:
  rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr subscription_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<DistanceSubscriber>();
  rclcpp::spin(node);
  node.reset();
  rclcpp::shutdown();
  return 0;
}
