cmake_minimum_required(VERSION 3.5)
project(hoainam_one)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # uncomment the line when a copyright and license is not present in all source files
  #set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # uncomment the line when this package is not in a git repo
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(
  DIRECTORY config description launch
  DESTINATION share/${PROJECT_NAME}
)
# Install launch files
install(DIRECTORY
  launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Install config files (nếu bạn muốn dùng rviz, nav2 params, ...)
install(DIRECTORY
  config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Install description (nếu dùng URDF/Xacro)
install(DIRECTORY
  description/
  DESTINATION share/${PROJECT_NAME}/description
)

install(PROGRAMS
  launch/plc_tcp_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME plc_tcp_bridge
)

install(PROGRAMS
  launch/plc_control_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME plc_control_node
)

install(PROGRAMS
  launch/map_speckle_filter.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME map_speckle_filter
)

install(PROGRAMS
  launch/odom_axis_corrector.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME odom_axis_corrector
)

ament_package()
