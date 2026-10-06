@echo off
rem Anonymous Docker credential helper for SSH sessions (public images only).
if "%1"=="get" (
  echo credentials not found in native keychain
  exit /b 1
)
if "%1"=="list" (
  echo {}
  exit /b 0
)
exit /b 0
