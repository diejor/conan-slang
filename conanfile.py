import os, glob
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.scm import Git
from conan.tools.files import (
    rmdir, collect_libs, copy, update_conandata,
)

class SlangConan(ConanFile):
    name         = "slang"
    version      = "2025.6.3"
    license      = "Apache-2.0"
    url          = "https://github.com/shader-slang/slang"
    homepage     = "https://shader-slang.org/"
    description  = "Slang is a shader tool and compiler for modern GPU shading languages."
    topics       = ("conan", "slang", "shader", "webgpu")

    settings     = "os", "compiler", "build_type", "arch"
    options      = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        git = Git(self)
        clone_args = [
            "--branch", data["commit"],      # checkout by SHA (or tag)
            "--single-branch",
            "--depth", "1",
            "--recursive",                   # pull submodules
        ]
        git.clone(url=data["url"], args=clone_args, target=".")
        rmdir(self, ".git")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"]       = "ON" if self.options.shared else "OFF"
        tc.variables["SLANG_LIB_TYPE"]         = "SHARED" if self.options.shared else "STATIC"
        if self.options.get_safe("fPIC"):
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"

        # keep debug info = OFF and LTO = OFF by default for *.a size reasons
        tc.variables["SLANG_ENABLE_RELEASE_DEBUG_INFO"] = "OFF"
        tc.variables["SLANG_ENABLE_RELEASE_LTO"]        = "OFF"

        # other feature flags
        tc.variables["SLANG_SLANG_LLVM_FLAVOR"]    = "DISABLE"
        tc.variables["SLANG_ENABLE_DXIL"]          = "OFF"
        tc.variables["SLANG_ENABLE_SLANGD"]        = "OFF"
        tc.variables["SLANG_ENABLE_GFX"]           = "OFF"
        tc.variables["SLANG_ENABLE_SLANG_GLSLANG"] = "OFF"
        tc.variables["SLANG_ENABLE_TESTS"]         = "OFF"
        tc.variables["SLANG_ENABLE_EXAMPLES"]      = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        build_type = str(self.settings.build_type)

        build_dirs = [
            self.build_folder,                                    # sometimes outputs to root
            os.path.join(self.build_folder, build_type),          # e.g. build/Release
            os.path.join(self.build_folder, "lib"),               # single-config Ninja/Make
            os.path.join(self.build_folder, build_type, "lib"),   # multi-config + lib subdir
        ]

        external_dirs = [
            os.path.join(self.build_folder, "external", "miniz"),
            os.path.join(self.build_folder, "external", "lz4", "build", "cmake"),
        ]
        for base in list(external_dirs):
            external_dirs.append(os.path.join(base, build_type))

        for d in build_dirs + external_dirs:
            if os.path.isdir(d):
                for pat in ("*.a", "*.lib"):
                    copy(self,
                         pattern=pat,
                         src=d,
                         dst=os.path.join(self.package_folder, "lib"),
                         keep_path=False)

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["slang"]
        else:
            # static link order
            self.cpp_info.libs = [
                "slang", "compiler-core", "core", "slang-cpp-parser",
                "slang-rt", "miniz", "lz4",
            ]
            self.cpp_info.defines = ["SLANG_STATIC"]

        self.cpp_info.set_property("cmake_target_name", "slang::slang")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["Advapi32", "Kernel32", "User32"]

