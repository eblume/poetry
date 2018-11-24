import os
import shutil
import sys
import tomlkit
from poetry.io import NullIO
from poetry.semver import Version
from poetry.utils._compat import Path
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv
from poetry.utils.toml_file import TomlFile


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir, config):
    venv_path = Path(tmp_dir) / "Virtual Env"

    EnvManager(config).build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


def test_env_get_in_project_venv(tmp_dir, environ, config):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (Path(tmp_dir) / ".venv").mkdir()

    venv = EnvManager(config).get(Path(tmp_dir))

    assert venv.path == Path(tmp_dir) / ".venv"


CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


def build_venv(path, executable=None):
    os.mkdir(path)


def remove_venv(path):
    shutil.rmtree(path)


def check_output_wrapper(version=Version.parse("3.7.1")):
    def check_output(cmd, *args, **kwargs):
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return "{}.{}".format(version.major, version.minor)
        else:
            return str(Path("/prefix"))

    return check_output


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.7", CWD, NullIO())
    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))

    m.assert_called_with(
        os.path.join(tmp_dir, "{}-py3.7".format(venv_name)), executable="python3.7"
    )

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")


def test_activate_activates_existing_virtualenv_no_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))

    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    m.assert_not_called()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")


def test_activate_activates_same_virtualenv_with_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])
    m = mocker.patch("poetry.utils.env.EnvManager.create_venv")

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")


def test_activate_activates_different_virtualenv_with_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))
    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.6", CWD, NullIO())

    m.assert_called_with(
        os.path.join(tmp_dir, "{}-py3.6".format(venv_name)), executable="python3.6"
    )

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

    assert env.path == Path(tmp_dir) / "{}-py3.6".format(venv_name)
    assert env.base == Path("/prefix")


def test_activate_activates_recreates_for_different_minor(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))
    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    build_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    remove_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.remove_venv", side_effect=remove_venv
    )

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    build_venv_m.assert_called_with(
        os.path.join(tmp_dir, "{}-py3.7".format(venv_name)), executable="python3.7"
    )
    remove_venv_m.assert_called_with(
        os.path.join(tmp_dir, "{}-py3.7".format(venv_name))
    )

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / "{}-py3.7".format(venv_name)).exists()


def test_deactivate_non_activated_but_existing(tmp_dir, config, mocker, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))

    (
        Path(tmp_dir)
        / "{}-py{}".format(venv_name, ".".join(str(c) for c in sys.version_info[:2]))
    ).mkdir()

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())

    EnvManager(config).deactivate(CWD, NullIO())
    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "{}-py{}".format(
        venv_name, ".".join(str(c) for c in sys.version_info[:2])
    )
    assert Path("/prefix")


def test_deactivate_activated(tmp_dir, config, mocker, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))
    version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor
    (
        Path(tmp_dir) / "{}-py{}.{}".format(venv_name, version.major, version.minor)
    ).mkdir()
    (
        Path(tmp_dir)
        / "{}-py{}.{}".format(venv_name, other_version.major, other_version.minor)
    ).mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {
        "minor": "{}.{}".format(other_version.major, other_version.minor),
        "patch": other_version.text,
    }
    envs_file.write(doc)

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())

    EnvManager(config).deactivate(CWD, NullIO())
    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "{}-py{}.{}".format(
        venv_name, version.major, version.minor
    )
    assert Path("/prefix")

    envs = envs_file.read()
    assert len(envs) == 0


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tmp_dir, config, mocker, environ
):
    environ["VIRTUAL_ENV"] = "/environment/prefix"

    venv_name = EnvManager.generate_env_name("simple_project", str(CWD))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])

    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")
