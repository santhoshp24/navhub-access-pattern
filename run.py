import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from navhub.__main__ import main

sys.exit(main())
