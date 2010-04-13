#!/bin/bash
pyflakes weboob scripts/* | grep -v __init__.py
