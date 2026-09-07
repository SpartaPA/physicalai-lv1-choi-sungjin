#include <chrono>
#include <cmath>
#include <functional>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "std_msgs/msg/float32.hpp"
#include "turtlesim/msg/pose.hpp"

using namespace std::chrono_literals;

class DistancePublisher : public rclcpp::Node
{
public:
  DistancePublisher()
  : Node("cpp_distance_publisher")
  {
    publish_rate_ = declare_parameter<double>("publish_rate", 10.0);
    if (publish_rate_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "publish_rate must be positive; using 10.0 Hz");
      publish_rate_ = 10.0;
    }

    const auto pose_topic = declare_parameter<std::string>("pose_topic", "/turtle1/pose");
    const auto distance_topic =
      declare_parameter<std::string>("distance_topic", "/turtle_distance");

    publisher_ = create_publisher<std_msgs::msg::Float32>(distance_topic, 10);
    subscription_ = create_subscription<turtlesim::msg::Pose>(
      pose_topic,
      10,
      [this](const turtlesim::msg::Pose::SharedPtr message) {
        latest_x_ = message->x;
        latest_y_ = message->y;
        pose_received_ = true;
      });

    create_publish_timer();

    parameter_callback_handle_ = add_on_set_parameters_callback(
      std::bind(&DistancePublisher::on_parameters, this, std::placeholders::_1));

    RCLCPP_INFO(
      get_logger(), "C++ distance publisher: %s -> %s at %.1f Hz",
      pose_topic.c_str(), distance_topic.c_str(), publish_rate_);
  }

private:
  void create_publish_timer()
  {
    const auto period = std::chrono::duration<double>(1.0 / publish_rate_);
    timer_ = create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(period),
      [this]() {
        if (!pose_received_) {
          return;
        }
        std_msgs::msg::Float32 message;
        message.data = static_cast<float>(std::hypot(latest_x_, latest_y_));
        publisher_->publish(message);
      });
  }

  rcl_interfaces::msg::SetParametersResult on_parameters(
    const std::vector<rclcpp::Parameter> & parameters)
  {
    rcl_interfaces::msg::SetParametersResult result;
    result.successful = true;

    for (const auto & parameter : parameters) {
      if (parameter.get_name() == "publish_rate") {
        const double requested_rate = parameter.as_double();
        if (requested_rate <= 0.0) {
          result.successful = false;
          result.reason = "publish_rate must be greater than zero";
          RCLCPP_WARN(get_logger(), "%s", result.reason.c_str());
          return result;
        }

        publish_rate_ = requested_rate;
        timer_->cancel();
        create_publish_timer();
        RCLCPP_INFO(get_logger(), "publish_rate changed to %.1f Hz", publish_rate_);
      }
    }
    return result;
  }

  double publish_rate_{10.0};
  double latest_x_{0.0};
  double latest_y_{0.0};
  bool pose_received_{false};
  rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr publisher_;
  rclcpp::Subscription<turtlesim::msg::Pose>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
  OnSetParametersCallbackHandle::SharedPtr parameter_callback_handle_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<DistancePublisher>();
  rclcpp::spin(node);
  node.reset();
  rclcpp::shutdown();
  return 0;
}
