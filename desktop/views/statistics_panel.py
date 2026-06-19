# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QSizePolicy
)

import pyqtgraph as pg
from pyqtgraph import PlotWidget, BarGraphItem


pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", subtitle: str = "", color: str = "#1976d2", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        self.setMinimumHeight(90)
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: #666; font-size: 12px;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        self.value_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        layout.addWidget(self.value_label)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet("color: #999; font-size: 11px;")
            layout.addWidget(self.subtitle_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class StatisticsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("数据统计")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        layout.addWidget(title)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(10)

        self.total_count_card = StatCard("发票总数", "0", "累计发票数量", "#1976d2")
        self.total_amount_card = StatCard("总金额", "¥ 0.00", "价税合计", "#388e3c")
        self.verified_card = StatCard("已核验", "0", "核验通过数量", "#7b1fa2")
        self.pending_card = StatCard("待处理", "0", "处理中/待核验", "#f57c00")
        self.invalid_card = StatCard("不合规", "0", "校验不通过", "#d32f2f")
        self.duplicate_card = StatCard("重复发票", "0", "重复录入数量", "#c62828")

        cards_layout.addWidget(self.total_count_card, 0, 0)
        cards_layout.addWidget(self.total_amount_card, 0, 1)
        cards_layout.addWidget(self.verified_card, 0, 2)
        cards_layout.addWidget(self.pending_card, 1, 0)
        cards_layout.addWidget(self.invalid_card, 1, 1)
        cards_layout.addWidget(self.duplicate_card, 1, 2)

        layout.addLayout(cards_layout)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(10)

        charts_layout.addWidget(self._create_monthly_chart(), 2)
        charts_layout.addWidget(self._create_type_chart(), 1)

        layout.addLayout(charts_layout, 1)

    def _create_monthly_chart(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: white; border-radius: 8px;")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("月度发票趋势")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        frame_layout.addWidget(title)

        self.monthly_plot = PlotWidget()
        self.monthly_plot.setBackground("w")
        self.monthly_plot.showGrid(x=False, y=True, alpha=0.3)
        self.monthly_plot.setLabel("left", "发票数量")
        self.monthly_plot.setLabel("bottom", "月份")
        self.monthly_plot.setMinimumHeight(250)

        self.monthly_plot.addLegend(offset=(30, 30))

        frame_layout.addWidget(self.monthly_plot, 1)
        return frame

    def _create_type_chart(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: white; border-radius: 8px;")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("发票类型分布")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        frame_layout.addWidget(title)

        self.type_plot = PlotWidget()
        self.type_plot.setBackground("w")
        self.type_plot.setMinimumHeight(250)
        self.type_plot.setAspectLocked()
        self.type_plot.hideAxis("left")
        self.type_plot.hideAxis("bottom")

        self.type_pie_item = pg.GraphicsLayout()
        self.type_plot.setCentralItem(self.type_pie_item)

        frame_layout.addWidget(self.type_plot, 1)
        return frame

    def update_statistics(self, stats: Dict[str, Any]):
        total_count = stats.get("total_count", 0)
        total_amount = stats.get("total_amount", 0)
        verified_count = stats.get("verified_count", 0)
        pending_count = stats.get("pending_count", 0)
        invalid_count = stats.get("invalid_count", 0)
        duplicate_count = stats.get("duplicate_count", 0)

        self.total_count_card.set_value(str(total_count))
        try:
            self.total_amount_card.set_value(f"¥ {float(total_amount):,.2f}")
        except Exception:
            self.total_amount_card.set_value(str(total_amount))
        self.verified_card.set_value(str(verified_count))
        self.pending_card.set_value(str(pending_count))
        self.invalid_card.set_value(str(invalid_count))
        self.duplicate_card.set_value(str(duplicate_count))

        self._update_monthly_chart(stats.get("monthly_data", {}))
        self._update_type_chart(stats.get("type_distribution", {}))

    def _update_monthly_chart(self, monthly_data: Dict[str, Dict[str, Any]]):
        self.monthly_plot.clear()

        if not monthly_data:
            return

        sorted_months = sorted(monthly_data.keys())
        months = list(range(len(sorted_months)))
        counts = [monthly_data[m].get("count", 0) for m in sorted_months]
        amounts = [monthly_data[m].get("amount", 0) for m in sorted_months]

        x_labels = [(i, m) for i, m in enumerate(sorted_months)]
        axis = self.monthly_plot.getAxis("bottom")
        axis.setTicks([x_labels])

        bar_item = BarGraphItem(
            x=months, height=counts, width=0.5,
            brush=pg.mkBrush("#1976d2"),
            pen=pg.mkPen("#1565c0")
        )
        self.monthly_plot.addItem(bar_item)

        pen = pg.mkPen(color="#388e3c", width=2)
        symbol_pen = pg.mkPen("#2e7d32")
        self.monthly_plot.plot(
            months, amounts,
            pen=pen, symbol="o", symbolSize=6,
            symbolBrush="#388e3c", symbolPen=symbol_pen,
            name="金额(元)"
        )

        self.monthly_plot.setYRange(0, max(counts) * 1.2 if counts else 10)

    def _update_type_chart(self, type_data: Dict[str, int]):
        self.type_plot.clear()
        self.type_pie_item = pg.GraphicsLayout()
        self.type_plot.setCentralItem(self.type_pie_item)

        if not type_data:
            return

        labels_map = {
            "vat_special": "增值税专票",
            "vat_general": "增值税普票",
            "vat_electronic": "电子发票",
            "general": "普通发票",
            "other": "其他",
            "unknown": "未知",
        }
        colors = ["#1976d2", "#388e3c", "#7b1fa2", "#f57c00", "#00838f", "#616161"]

        pie_chart = self.type_pie_item.addPlot()
        pie_chart.setAspectLocked()
        pie_chart.hideAxis("left")
        pie_chart.hideAxis("bottom")

        total = sum(type_data.values())
        if total == 0:
            return

        angle = 0
        color_idx = 0
        for inv_type, count in type_data.items():
            if count <= 0:
                continue
            span_angle = count / total * 360
            color = colors[color_idx % len(colors)]
            color_idx += 1

            ellipse = pg.QtWidgets.QGraphicsEllipseItem(-1, -1, 2, 2)
            ellipse.setBrush(pg.mkBrush(color))
            ellipse.setPen(pg.mkPen("w", width=1))
            ellipse.setStartAngle(angle * 16)
            ellipse.setSpanAngle(span_angle * 16)
            pie_chart.addItem(ellipse)

            angle += span_angle

        legend = pg.LegendItem(offset=(50, 20))
        legend.setParentItem(pie_chart)
        color_idx = 0
        for inv_type, count in type_data.items():
            if count <= 0:
                continue
            label = labels_map.get(inv_type, inv_type)
            color = colors[color_idx % len(colors)]
            color_idx += 1
            sample = pg.PlotDataItem(
                symbol="s", symbolSize=12,
                symbolBrush=color, pen=None
            )
            pie_chart.addItem(sample)
            legend.addItem(sample, f"{label}: {count}")
