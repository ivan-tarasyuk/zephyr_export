import json as json_module
from pathlib import Path
from typing import Callable, Optional

import aiofiles

from shared.exceptions import FileNotFound, InvalidData, IOException


def safe_async(func: Callable) -> Callable:
    async def wrapper(*args, **kwargs) -> Optional:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(str(e))
            return
    return wrapper


async def read_json(file_path: Path) -> dict:
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            content = await file.read()
            return json_module.loads(content)
    except FileNotFoundError:
        raise FileNotFound(f'[ERROR] JSON file not found at {file_path}')
    except json_module.JSONDecodeError as e:
        raise InvalidData(f'[ERROR] Failed to decode JSON file {file_path}. {e}')
    except Exception as e:
        raise IOException(f'[ERROR] An error occurred while reading JSON file {file_path}. {e}')


async def write_json(file_path: Path, data: dict) -> None:
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            content = json_module.dumps(data, ensure_ascii=False, indent=2)
            await file.write(content)
    except Exception as e:
        raise IOException(f'[ERROR] An error occurred while writing to {file_path}. {e}')
