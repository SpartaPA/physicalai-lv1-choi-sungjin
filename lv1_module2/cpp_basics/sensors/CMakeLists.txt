cmake_minimum_required(VERSION 3.10)
project(sensors_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(enable_assignment_warnings target_name)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(${target_name} PRIVATE
            -Wall
            -Wextra
            -Wpedantic
            -Wnon-virtual-dtor
        )
    endif()
endfunction()

# 정상 제출용 실행 파일
add_executable(sensors_app main.cpp)
target_include_directories(sensors_app PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
enable_assignment_warnings(sensors_app)

# 메모리 누수 전후를 AddressSanitizer로 확인하는 실행 파일
add_executable(sensors_asan main.cpp)
target_include_directories(sensors_asan PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
enable_assignment_warnings(sensors_asan)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(sensors_asan PRIVATE
        -fsanitize=address
        -fno-omit-frame-pointer
    )
    target_link_options(sensors_asan PRIVATE -fsanitize=address)
endif()

# 가상 소멸자를 뺐을 때의 차이를 관찰하기 위한 실험 전용 실행 파일
add_executable(sensors_no_virtual main.cpp)
target_include_directories(sensors_no_virtual PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(sensors_no_virtual PRIVATE
    SENSOR_DEMO_NON_VIRTUAL_DESTRUCTOR
)
enable_assignment_warnings(sensors_no_virtual)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(sensors_no_virtual PRIVATE
        -fsanitize=address
        -fno-omit-frame-pointer
    )
    target_link_options(sensors_no_virtual PRIVATE -fsanitize=address)
endif()
