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

    def _copy_archives(self, patterns):
        cand_dirs = [
            os.path.join(self.build_folder, "lib"),
            os.path.join(self.build_folder, str(self.settings.build_type), "lib"),
        ]
        for d in cand_dirs:
            for pat in patterns:
                for f in glob.glob(os.path.join(d, pat)):
                    copy(self, os.path.basename(f),
                         src=d, dst=os.path.join(self.package_folder, "lib"))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if not self.options.shared:
            # pick up the extra .a files we need
            self._copy_archives(["libcore*.a",
                                 "libcompiler-core*.a",
                                 "libslang-cpp-parser*.a"])
            # third-party
            copy(self, "libminiz*.a",
                 src=os.path.join(self.build_folder, "external", "miniz"),
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "liblz4*.a",
                 src=os.path.join(self.build_folder,
                                  "external", "lz4", "build", "cmake"),
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["slang"]
        else:
            # static link order
            self.cpp_info.libs = [
                "slang", "compiler-core", "core", "slang-cpp-parser",
                "slang-rt", "miniz", "lz4",
            ]
        self.cpp_info.set_property("cmake_target_name", "slang::slang")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["Advapi32", "Kernel32", "User32"]

