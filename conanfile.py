import os, glob
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.scm import Git
from conan.tools.files import (
    rmdir, collect_libs, copy, update_conandata,
)

class SlangConan(ConanFile):
    name         = "slang"
    version      = "2025.13.1"
    license      = "Apache-2.0"
    url          = "https://github.com/shader-slang/slang"
    homepage     = "https://shader-slang.org/"
    description  = "Slang is a shader tool and compiler for modern GPU shading languages."
    topics       = ("conan", "slang", "shader", "webgpu")

    settings     = "os", "compiler", "build_type", "arch"
    options      = { "fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        git = Git(self)
        clone_args = [
            "--branch", f"v{self.version}",
            "--single-branch", "--depth", "1", "--recursive"
        ]
        git.clone(self.url, args=clone_args, target=".")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        if self.options.get_safe("fPIC"):
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()


    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "slang")
        self.cpp_info.set_property("cmake_target_name", "slang::slang")
