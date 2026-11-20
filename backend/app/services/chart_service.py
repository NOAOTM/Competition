from pathlib import Path
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def read_table(source: Path) -> pd.DataFrame:
    if source.suffix.lower() == ".csv":
        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return pd.read_csv(source, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(f"CSV 编码无法识别：{last_error}")
    if source.suffix.lower() == ".xlsx":
        return pd.read_excel(source)
    raise ValueError("目前图表数据支持 CSV 和 XLSX")


def create_chart(
    source: Path,
    output_dir: Path,
    chart_type: str,
    x_column: str,
    y_column: str,
    z_column: str | None = None,
) -> Path:
    frame = read_table(source)
    if frame.empty:
        raise ValueError("文件中没有数据行")
    for column in (x_column, y_column, z_column):
        if column and column not in frame.columns:
            raise ValueError(f"找不到数据列：{column}")
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure = plt.figure(figsize=(10, 5.625), dpi=144)
    axis = figure.add_subplot(111)
    if chart_type == "line":
        axis.plot(frame[x_column], frame[y_column], marker="o", color="#28775c")
    elif chart_type == "bar":
        axis.bar(frame[x_column].astype(str), frame[y_column], color="#58a27d")
    elif chart_type == "pie":
        axis.pie(frame[y_column], labels=frame[x_column].astype(str), autopct="%1.1f%%")
    elif chart_type == "scatter":
        axis.scatter(frame[x_column], frame[y_column], c="#28775c", alpha=0.8)
    elif chart_type == "3d":
        if not z_column:
            raise ValueError("3D 图表需要选择 Z 轴数据列")
        axis.remove()
        axis = figure.add_subplot(111, projection="3d")
        axis.scatter(frame[x_column], frame[y_column], frame[z_column], c="#28775c")
        axis.set_zlabel(z_column)
    else:
        raise ValueError("图表类型只支持 line、bar、pie、scatter、3d")
    if chart_type != "pie":
        axis.set_xlabel(x_column)
        axis.set_ylabel(y_column)
        axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    result = output_dir / f"chart-{uuid4().hex}.png"
    figure.savefig(result, format="png", facecolor="white", bbox_inches="tight")
    plt.close(figure)
    return result
