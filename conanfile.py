import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.scm import Git
from conan.tools.files import copy, rm, mkdir, collect_libs


class SlangConan(ConanFile):
    name = "slang"
    version = "2025.13.1"
    license = "Apache-2.0"
    url = "https://github.com/shader-slang/slang"
    homepage = "https://shader-slang.org/"
    description = "Slang is a shader tool and compiler for modern GPU shading languages."
    topics = ("conan", "slang", "shader", "webgpu")

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        Git(self).clone(
            self.url,
            args=[
                "--branch", f"v{self.version}",
                "--single-branch", "--depth", "1", "--recursive",
            ],
            target=".",
        )

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        if self.options.get_safe("fPIC"):
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        if str(self.settings.os) == "Macos":
            tc.variables["CMAKE_MACOSX_RPATH"] = "ON"

        tc.cache_variables["SLANG_ENABLE_SLANG_RHI"] = False
        tc.cache_variables["SLANG_ENABLE_TESTS"] = False
        tc.cache_variables["SLANG_ENABLE_EXAMPLES"] = False
        tc.cache_variables["SLANG_ENABLE_GFX"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        pkg = Path(self.package_folder)
        plugin_exts = {".dll", ".so", ".dylib", ".bundle"}
        fragments = {"slang-glsl", "slang_glsl", "slang-glslang", "-module", "plugin"}
        roots = [pkg / "lib", pkg / "lib64", pkg / "bin"]

        def is_plugin(p: Path) -> bool:
            n = p.name.lower()
            return p.suffix.lower() in plugin_exts and any(f in n for f in fragments)

        candidates = []
        for root in roots:
            if root.is_dir():
                for p in root.rglob("*"):
                    if p.is_file() and is_plugin(p):
                        candidates.append(p)

        if candidates:
            plugindir = pkg / "plugins"
            mkdir(self, str(plugindir))
            for p in candidates:
                copy(self, p.name, src=str(p.parent), dst=str(plugindir))
                rm(self, p.name, folder=str(p.parent))

    def package_info(self):
        collected = set(collect_libs(self))
        preferred = ["gfx", "gfx-core", "gfx-base", "slang-rt", "slang"]
        libs = [n for n in preferred if n in collected]

        def is_pluginish(n: str) -> bool:
            n = n.lower()
            return any(f in n for f in ("glsl", "glslang", "module", "plugin"))

        libs += [n for n in sorted(collected) if n not in libs and not is_pluginish(n)]
        self.cpp_info.libs = libs

        self.cpp_info.set_property("cmake_file_name", "slang")
        self.cpp_info.set_property("cmake_target_name", "slang::slang")

        plugin_path = os.path.join(self.package_folder, "plugins")
        if os.path.isdir(plugin_path):
            self.runenv_info.define_path("SLANG_PLUGIN_PATH", plugin_path)
