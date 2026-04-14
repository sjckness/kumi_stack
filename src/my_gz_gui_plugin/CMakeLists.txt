cmake_minimum_required(VERSION 3.10)
project(my_gz_gui_plugin)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(gz-gui8 REQUIRED)
find_package(gz-transport13 REQUIRED)
find_package(gz-msgs10 REQUIRED)
find_package(gz-sim8 REQUIRED)

qt5_add_resources(QRC_SOURCES qml/qml.qrc)
qt5_wrap_cpp(MOC_SOURCES include/my_gz_gui_plugin/MyGuiPlugin.hh)

add_library(${PROJECT_NAME} SHARED
  src/MyGuiPlugin.cc
  ${MOC_SOURCES}
  ${QRC_SOURCES}
)

target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

target_link_libraries(${PROJECT_NAME}
  ament_index_cpp::ament_index_cpp
  gz-gui8::gz-gui8
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-sim8::gz-sim8
)

ament_target_dependencies(${PROJECT_NAME}
  rclcpp
  std_msgs
)

install(
  TARGETS ${PROJECT_NAME}
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)

install(
  DIRECTORY include/
  DESTINATION include
)

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/my_gz_gui_plugin.dsv"
  "${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/my_gz_gui_plugin.sh"
)

ament_package()
