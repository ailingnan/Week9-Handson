"""
Smoke tests for fundamental configuration and module loading.
Run via: python3 -m unittest tests/smoke_test.py
"""

import os
import sys
import unittest
import importlib
import yaml

# Ensure the root path is correct so we can import 'core', 'app', etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestSystemConfig(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_config_yaml_exists(self):
        """Verify config/config.yaml exists and loads correctly."""
        config_path = os.path.join(self.root_dir, "config", "config.yaml")
        self.assertTrue(os.path.exists(config_path), "config.yaml is missing")
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        self.assertIn("llm_model", cfg)
        self.assertIn("snowflake", cfg)

    def test_required_environment_variables(self):
        """Verify essential environment variables exist (without making network calls)."""
        from dotenv import load_dotenv
        load_dotenv(os.path.join(self.root_dir, ".env"))
        
        required_vars = ["GROQ_API_KEY", "SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_ACCOUNT"]
        for var in required_vars:
            val = os.getenv(var)
            self.assertIsNotNone(val, f"Required environment variable {var} is missing.")
            self.assertNotEqual(val.strip(), "", f"Required environment variable {var} is empty.")

    def test_directories_exist(self):
        """Verify required directories exist or can be created."""
        for d in ["logs", "artifacts"]:
            dir_path = os.path.join(self.root_dir, d)
            os.makedirs(dir_path, exist_ok=True)
            self.assertTrue(os.path.exists(dir_path), f"Failed to create directory {d}")

    def test_logger_initialization(self):
        """Verify that the logger initializes without crashing."""
        try:
            from core.logger import get_logger
            log = get_logger("test_logger")
            self.assertIsNotNone(log)
            self.assertTrue(len(log.handlers) > 0)
        except Exception as e:
            self.fail(f"Logger failed to initialize: {e}")

    def test_groq_client_initialization(self):
        """Verify that the Groq library can instantiate without dependency conflicts (e.g. httpx version issues)."""
        try:
            from groq import Groq
            # Instantiate with a dummy key just to see if the HTTP client crashes on init
            _ = Groq(api_key="sk-dummy-test-key")
        except Exception as e:
            self.fail(f"Groq client failed to initialize (Sub-dependency conflict likely): {e}")

    def test_core_module_imports(self):
        """Ensure refactored modules can be imported correctly."""
        modules_to_check = [
            "core.features.feature_store",
            "core.modeling.evaluator",
            "core.ingestion.scheduler",
            "app.core_services",
            "agent.agent_runner",
            "agent.tools"
        ]
        
        for mod in modules_to_check:
            with self.subTest(module=mod):
                try:
                    importlib.import_module(mod)
                except ImportError as e:
                    self.fail(f"Could not import {mod}: {e}")

if __name__ == "__main__":
    unittest.main()
