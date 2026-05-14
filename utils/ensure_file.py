from pathlib import Path


def ensure_save_path(save_path: str):
    """
    确保 save_path 的父目录存在
    """

    save_path = Path(save_path)

    # 创建父目录
    save_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return save_path
