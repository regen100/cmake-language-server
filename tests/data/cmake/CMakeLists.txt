cmake_minimum_required(VERSION 3.10)

project(testproject CXX)

add_executable(test_app main.cpp)

add_library(test_lib lib.cpp)
