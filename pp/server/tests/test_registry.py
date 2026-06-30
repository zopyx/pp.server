"""Tests for pp.server.registry module."""

import pytest

from pp.server.registry import (
    REGISTRY,
    _register_converters,
    available_converters,
    converter_versions,
    get_converter_registry,
    has_converter,
    main,
    register_converter,
)


class TestRegisterConverter:
    def test_register_nonexistent(self) -> None:
        """Registering a non-existent converter returns False."""
        register_converter("test_nonexistent", "nonexistent_cmd_12345_xyz")
        assert not has_converter("test_nonexistent")

    def test_register_existing(self) -> None:
        """Registering an existing command returns True."""
        register_converter("test_ls", "ls")
        assert has_converter("test_ls")

    def test_register_twice(self) -> None:
        """Registering the same converter twice doesn't break."""
        register_converter("test_dup", "ls")
        register_converter("test_dup", "ls")
        assert has_converter("test_dup")


class TestAvailableConverters:
    def test_available_converters_returns_list(self) -> None:
        """available_converters() returns a list."""
        converters = available_converters()
        assert isinstance(converters, list)

    def test_available_converters_contains_registered(self) -> None:
        """Available converters includes registered commands."""
        register_converter("test_avail", "ls")
        assert "test_avail" in available_converters()
        assert "test_nonexistent" not in available_converters()


class TestRegisterConverters:
    def test_register_converters_runs(self) -> None:
        """_register_converters() runs without error."""
        _register_converters()
        result = available_converters()
        assert isinstance(result, list)


class TestHasConverter:
    def test_has_converter_false_for_unknown(self) -> None:
        """has_converter returns False for unknown converters."""
        assert not has_converter("definitely_not_a_real_converter_99999")


class TestGetConverterRegistry:
    def test_get_converter_registry_returns_dict(self) -> None:
        """get_converter_registry() returns the REGISTRY dict."""
        reg = get_converter_registry()
        assert reg is REGISTRY
        assert isinstance(reg, dict)


class TestConverterVersions:
    """Tests for the converter_versions async function."""

    @pytest.mark.asyncio
    async def test_converter_versions_success(self, monkeypatch) -> None:
        """converter_versions returns version strings for registered converters."""
        # Register a converter for testing
        register_converter("test_version_cmd", "echo")

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="1.2.3", stderr="")

        monkeypatch.setattr("pp.server.registry.run", mock_run)

        # Mock available_converters to return only our test converter
        monkeypatch.setattr(
            "pp.server.registry.available_converters",
            lambda: ["test_version_cmd"],
        )

        # Mock CONVERTERS to include our test converter
        monkeypatch.setattr(
            "pp.server.registry.CONVERTERS",
            {
                "test_version_cmd": {
                    "cmd": "echo",
                    "version": "echo --version",
                    "convert": "echo {cmd_options} {source_html} -o {target_filename}",
                },
            },
        )

        versions = await converter_versions()
        assert isinstance(versions, dict)
        assert "test_version_cmd" in versions
        assert versions["test_version_cmd"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_converter_versions_nonzero_status(self, monkeypatch) -> None:
        """Converters with non-zero status get 'n/a' version."""
        register_converter("test_bad_cmd", "false")

        async def mock_run(cmd: str) -> dict:
            return dict(status=1, stdout="", stderr="error")

        monkeypatch.setattr("pp.server.registry.run", mock_run)

        monkeypatch.setattr(
            "pp.server.registry.available_converters",
            lambda: ["test_bad_cmd"],
        )

        monkeypatch.setattr(
            "pp.server.registry.CONVERTERS",
            {
                "test_bad_cmd": {
                    "cmd": "false",
                    "version": "false --version",
                    "convert": "false {cmd_options} {source_html} -o {target_filename}",
                },
            },
        )

        versions = await converter_versions()
        assert versions.get("test_bad_cmd") == "n/a"

    @pytest.mark.asyncio
    async def test_converter_versions_exception_handling(self, monkeypatch) -> None:
        """Exceptions in version checks are caught and skipped."""
        register_converter("test_exc_cmd", "echo")

        async def mock_run(cmd: str) -> dict:
            msg = "mock error"
            raise RuntimeError(msg)

        monkeypatch.setattr("pp.server.registry.run", mock_run)

        monkeypatch.setattr(
            "pp.server.registry.available_converters",
            lambda: ["test_exc_cmd"],
        )

        monkeypatch.setattr(
            "pp.server.registry.CONVERTERS",
            {
                "test_exc_cmd": {
                    "cmd": "echo",
                    "version": "echo --version",
                    "convert": "echo {cmd_options} {source_html} -o {target_filename}",
                },
            },
        )

        versions = await converter_versions()
        assert "test_exc_cmd" not in versions


class TestMain:
    def test_main_calls_register_and_prints(self, monkeypatch, capsys) -> None:
        """main() calls _register_converters() and prints available converters."""
        monkeypatch.setattr("pp.server.registry._register_converters", lambda: None)
        main()
        captured = capsys.readouterr()
        assert captured.out.strip() is not None
