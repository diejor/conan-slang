import os
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git

class SlangConan(ConanFile):
    name = "slang"
    version = "2025.6.3"
    author = "shader-slang"  
    description = "Slang is a shader tool and compiler for modern GPU shading languages."
    topics = ("conan", "slang", "shader", "webgpu")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    export_sources = "LICENSE*", "LICENSES/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Checkout the Slang repository at the specific tag, initializing submodules with --recursive.
        git = Git(self)
        git.clone(url="https://github.com/shader-slang/slang.git",
                  branch="v2025.6.3",
                  args="--recursive",
                  target=".")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # Enable generation of release builds with debug info (similar to releaseWithDebugInfo preset).
        tc.variables["SLANG_ENABLE_RELEASE_DEBUG_INFO"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        if self.settings.os == "Windows":
            # Optionally add Windows-specific flags.
            cmake.configure(variables={"CMAKE_CXX_FLAGS": "/utf-8"})
        else:
            cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Define the exported CMake target.
        self.cpp_info.set_property("cmake_target_name", "slang::slang")
        self.cpp_info.libs = ["slang"]

