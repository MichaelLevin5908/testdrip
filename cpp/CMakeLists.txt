cmake_minimum_required(VERSION 3.14)
project(drip-health-cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Path to the SDK in the monorepo
set(DRIP_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../cpp-sdk"
    CACHE PATH "Path to drip-sdk-cpp source directory")

# Add the SDK as a subdirectory
add_subdirectory(${DRIP_SDK_DIR} drip-sdk EXCLUDE_FROM_ALL)

# Health check binary
add_executable(drip-health main.cpp)
target_link_libraries(drip-health PRIVATE drip_sdk)

# ML training integration tests
add_executable(drip-ml-test ml_training_test.cpp)
target_link_libraries(drip-ml-test PRIVATE drip_sdk)
