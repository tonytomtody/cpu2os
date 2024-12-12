import re
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple
import random
import math

@dataclass
class Pin:
    name: str
    is_input: bool
    is_output: bool
    net: str = None
    x: float = 0
    y: float = 0

@dataclass
class Cell:
    name: str
    cell_type: str
    pins: List[Pin]
    width: float = 1
    height: float = 1
    x: float = 0
    y: float = 0

@dataclass
class Net:
    name: str
    source_pin: Pin = None
    sink_pins: List[Pin] = None

class SimpleRouter:
    def __init__(self):
        self.cells: Dict[str, Cell] = {}
        self.nets: Dict[str, Net] = {}
        self.die_width = 100
        self.die_height = 100
        self.grid_size = 1

    def parse_yosys(self, netlist_str: str):
        """解析 Yosys 輸出的網表"""
        # 解析模組定義
        module_match = re.search(r'module\s+(\w+)\((.*?)\);', netlist_str, re.DOTALL)
        if not module_match:
            raise ValueError("無法找到模組定義")

        module_name = module_match.group(1)
        ports = module_match.group(2).split(',')
        
        # 解析端口定義
        input_ports = set()
        output_ports = set()
        for line in netlist_str.split('\n'):
            if 'input' in line:
                match = re.search(r'input\s+(?:\[\d+:\d+\])?\s*(\w+)', line)
                if match:
                    input_ports.add(match.group(1))
            elif 'output' in line:
                match = re.search(r'output\s+(?:\[\d+:\d+\])?\s*(\w+)', line)
                if match:
                    output_ports.add(match.group(1))

        # 解析 assign 語句
        assign_pattern = r'assign\s+(\w+)\s*=\s*(.+?);'
        for match in re.finditer(assign_pattern, netlist_str):
            output_wire = match.group(1)
            expression = match.group(2)
            
            # 創建邏輯門單元
            cell_name = f"cell_{output_wire}"
            pins = []
            
            # 添加輸出管腳
            pins.append(Pin(output_wire, False, True))
            
            # 查找輸入信號
            input_signals = re.findall(r'[ab]\[\d\]|\w+(?<!&)(?<!\|)(?<!\^)(?<!\()', expression)
            for signal in input_signals:
                if signal not in ('&', '|', '^', '~'):
                    pins.append(Pin(signal, True, False))
            
            cell = Cell(cell_name, "LOGIC", pins)
            self.cells[cell_name] = cell

    def place_cells(self):
        """簡單的單元放置算法 (Simple cell placement algorithm)
        使用網格式放置策略，將電路單元均勻分布在晶片上
        """
        # 計算需要放置的總單元數
        num_cells = len(self.cells)
        
        # 計算網格的邊長
        # 例如：9個單元會得到 3x3 的網格，12個單元會得到 4x4 的網格
        # math.ceil 確保有足夠的網格空間放置所有單元
        grid_size = math.ceil(math.sqrt(num_cells))
        
        # 初始化放置位置為左下角
        current_x = 0  # 當前網格的 x 座標（從0開始）
        current_y = 0  # 當前網格的 y 座標（從0開始）
        
        # 計算每個網格的實際寬度和高度
        # 例如：如果晶片大小是 100x100，網格大小是 4，
        # 則每個網格是 25x25 的大小
        grid_width = self.die_width / grid_size   # 單個網格的寬度
        grid_height = self.die_height / grid_size  # 單個網格的高度
        
        # 遍歷所有需要放置的單元
        for cell in self.cells.values():
            # 計算單元的實際放置座標
            # 將單元放在網格的中心點
            # 例如：對於第一個網格(0,0)，如果網格大小是25x25
            # 則單元會被放置在 (12.5, 12.5) 的位置
            cell.x = current_x * grid_width + grid_width/2   # 單元的 x 座標
            cell.y = current_y * grid_height + grid_height/2 # 單元的 y 座標
            
            # 移動到下一個網格位置
            current_x += 1
            
            # 如果到達當前行的末尾
            # 則移動到下一行的開始位置
            if current_x >= grid_size:  # 若已到達行尾
                current_x = 0           # x 座標重置到行首
                current_y += 1          # y 座標增加，移到下一行

    def route_nets(self):
        """簡單的布線算法 - 使用曼哈頓路徑（Manhattan routing）
        為每個輸出管腳找到對應的輸入管腳，並在它們之間創建布線路徑
        """
        routes = []  # 存儲所有布線路徑的列表
        
        # 遍歷所有電路單元
        for cell in self.cells.values():
            # 遍歷當前單元的所有管腳
            for pin in cell.pins:
                # 只處理輸出管腳
                if pin.is_output:
                    # 找到這個輸出管腳需要連接的所有輸入管腳
                    for target_cell in self.cells.values():
                        for target_pin in target_cell.pins:
                            # 檢查是否為匹配的輸入管腳（名稱相同的輸入管腳）
                            if target_pin.is_input and target_pin.name == pin.name:
                                # 為這對管腳創建曼哈頓布線路徑
                                route = self.create_manhattan_route(
                                    (cell.x, cell.y),        # 起點：輸出管腳所在單元的位置
                                    (target_cell.x, target_cell.y)  # 終點：輸入管腳所在單元的位置
                                )
                                # 將布線信息添加到結果列表
                                routes.append((pin.name, route))
        return routes

    def create_manhattan_route(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """創建簡單的曼哈頓路徑（Manhattan path）
        
        參數:
            start (Tuple[float, float]): 起點座標 (x1, y1)
            end (Tuple[float, float]): 終點座標 (x2, y2)
        
        返回:
            List[Tuple[float, float]]: 包含三個點的曼哈頓路徑
                - 起點
                - 轉折點
                - 終點
        """
        x1, y1 = start  # 解包起點座標
        x2, y2 = end    # 解包終點座標
        
        # 返回三個點來定義曼哈頓路徑：
        # 1. start: 起點 (x1, y1)
        # 2. (x2, y1): 轉折點，x座標已到達終點，y座標還在起點
        # 3. end: 終點 (x2, y2)
        return [
            start,      # 路徑起點
            (x2, y1),   # 轉折點（先水平移動）
            end         # 路徑終點
        ]

    def generate_def(self) -> str:
        """生成簡化的 DEF 格式輸出"""
        def_content = []
        def_content.append("VERSION 5.8 ;")
        def_content.append(f"DESIGN top ;")
        def_content.append(f"UNITS DISTANCE MICRONS 1000 ;")
        def_content.append(f"DIEAREA ( 0 0 ) ( {self.die_width} {self.die_height} ) ;")
        
        # 添加單元放置信息
        def_content.append(f"COMPONENTS {len(self.cells)} ;")
        for cell in self.cells.values():
            def_content.append(f"- {cell.name} {cell.cell_type}")
            def_content.append(f"  + PLACED ( {int(cell.x)} {int(cell.y)} ) N ;")
        def_content.append("END COMPONENTS")
        
        # 添加布線信息
        routes = self.route_nets()
        def_content.append(f"NETS {len(routes)} ;")
        for net_name, route in routes:
            def_content.append(f"- {net_name}")
            path_str = " ".join([f"( {int(x)} {int(y)} )" for x, y in route])
            def_content.append(f"  + ROUTED {path_str} ;")
        def_content.append("END NETS")
        
        def_content.append("END DESIGN")
        return "\n".join(def_content)

# 使用示例
def place_route(netlist_str: str):
    router = SimpleRouter()
    router.parse_yosys(netlist_str)
    router.place_cells()
    router.generate_def()
    return router

# 讀取 Yosys 網表
with open('netlist.v', 'r') as f:
    netlist_str = f.read()

# 創建並運行工具
router = place_route(netlist_str)

# 生成 DEF 文件
def_content = router.generate_def()
with open('output.def', 'w') as f:
    f.write(def_content)