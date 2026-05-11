__all__ = ["PineScriptParser", "PineScriptStrategy"]

from typing import Dict, List, Any, Optional, Callable
import re
import pandas as pd
from ..utils.logger import logger

class PineScriptParser:
    def __init__(self):
        self.source_code = ""
        self.version = 5
        self.indicators = {}
        self.strategies = {}
        self.inputs = {}
        self.variables = {}
        self.functions = {}

    def parse(self, pine_script: str) -> Dict[str, Any]:
        self.source_code = pine_script
        self._reset()

        pine_script = self._remove_comments(pine_script)

        self._detect_version(pine_script)
        self._parse_inputs(pine_script)
        self._parse_variables(pine_script)
        self._parse_functions(pine_script)
        self._parse_indicators(pine_script)
        self._parse_strategies(pine_script)

        return {
            'version': self.version,
            'inputs': self.inputs,
            'variables': self.variables,
            'functions': self.functions,
            'indicators': self.indicators,
            'strategies': self.strategies
        }

    def _reset(self):
        self.inputs = {}
        self.variables = {}
        self.functions = {}
        self.indicators = {}
        self.strategies = {}

    def _remove_comments(self, code: str) -> str:
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code

    def _detect_version(self, code: str):
        match = re.search(r'//@version\s*(\d+)', code)
        if match:
            self.version = int(match.group(1))

    def _parse_inputs(self, code: str):
        input_patterns = [
            r'input\.(?:int|float|bool|string)=(.+?)(?:;|\n)',
            r'input\s*\(\s*(\w+)\s*,\s*["\'](.+?)["\']',
        ]

        for pattern in input_patterns:
            for match in re.finditer(pattern, code):
                if 'input.int' in match.group(0) or 'input.float' in match.group(0):
                    var_name = self._extract_var_name(match.group(0))
                    value = self._extract_value(match.group(0))
                    self.inputs[var_name] = {'type': 'number', 'value': float(value) if value else 0}
                elif 'input.bool' in match.group(0):
                    var_name = self._extract_var_name(match.group(0))
                    value = match.group(0).lower().find('true') > -1
                    self.inputs[var_name] = {'type': 'bool', 'value': value}

    def _extract_var_name(self, code: str) -> str:
        match = re.search(r'(\w+)\s*=', code)
        return match.group(1) if match else 'unknown'

    def _extract_value(self, code: str) -> str:
        match = re.search(r'=\s*(.+?)(?:;|$)', code)
        return match.group(1).strip() if match else '0'

    def _parse_variables(self, code: str):
        var_pattern = r'(?:float|int|bool)\s+(\w+)\s*=\s*(.+?)(?:;|$)'
        for match in re.finditer(var_pattern, code):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            self.variables[var_name] = var_value

    def _parse_functions(self, code: str):
        func_pattern = r'(?:float|int|var)\s+(\w+)\s*\(([^)]*)\)\s*=>\s*(.+)'
        for match in re.finditer(func_pattern, code):
            func_name = match.group(1)
            func_args = [a.strip() for a in match.group(2).split(',') if a.strip()]
            func_body = match.group(3)
            self.functions[func_name] = {'args': func_args, 'body': func_body}

    def _parse_indicators(self, code: str):
        indicator_pattern = r'(?:indicator|study)\s*\([^)]*\)'
        for match in re.finditer(indicator_pattern, code):
            self.indicators['main'] = {'source': match.group(0)}

    def _parse_strategies(self, code: str):
        strategy_pattern = r'strategy\s*\([^)]*\)'
        for match in re.finditer(strategy_pattern, code):
            self.strategies['main'] = {'source': match.group(0)}


class PineScriptEngine:
    def __init__(self, parsed_script: Dict[str, Any]):
        self.parsed = parsed_script
        self.context = {}
        self._setup_context()

    def _setup_context(self):
        for name, spec in self.parsed.get('inputs', {}).items():
            self.context[name] = spec.get('value', 0)

        for name, value in self.parsed.get('variables', {}).items():
            self.context[name] = self._evaluate_expression(value)

    def _evaluate_expression(self, expr: str) -> Any:
        expr = expr.strip()

        if expr.startswith('input.'):
            parts = expr.split('.')
            if len(parts) > 1:
                return self.context.get(parts[1], 0)

        if re.match(r'^-?\d+\.?\d*$', expr):
            return float(expr)

        if expr in self.context:
            return self.context[expr]

        if '+' in expr:
            parts = expr.split('+')
            return sum(self._evaluate_expression(p) for p in parts)

        if '-' in expr and expr.count('-') == 1:
            parts = expr.split('-')
            if len(parts) == 2:
                return self._evaluate_expression(parts[0]) - self._evaluate_expression(parts[1])

        if '*' in expr:
            parts = expr.split('*')
            result = 1
            for p in parts:
                result *= self._evaluate_expression(p)
            return result

        if '/' in expr:
            parts = expr.split('/')
            result = self._evaluate_expression(parts[0])
            for p in parts[1:]:
                result /= self._evaluate_expression(p)
            return result

        return 0

    def calculate_indicator(self, data: pd.DataFrame, indicator_name: str) -> pd.Series:
        if indicator_name.startswith('ta.sma'):
            period = self._extract_ta_period(indicator_name)
            return data['close'].rolling(window=period).mean()

        elif indicator_name.startswith('ta.ema'):
            period = self._extract_ta_period(indicator_name)
            return data['close'].ewm(span=period, adjust=False).mean()

        elif indicator_name.startswith('ta.rsi'):
            period = self._extract_ta_period(indicator_name)
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        elif indicator_name.startswith('ta.macd'):
            fast, slow, signal = 12, 26, 9
            ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return histogram

        elif indicator_name.startswith('ta.bb'):
            period = self._extract_ta_period(indicator_name)
            sma = data['close'].rolling(window=period).mean()
            std = data['close'].rolling(window=period).std()
            return sma + 2 * std

        elif indicator_name.startswith('ta.atr'):
            high, low, close = data['high'], data['low'], data['close']
            tr = pd.concat([
                high - low,
                abs(high - close.shift()),
                abs(low - close.shift())
            ], axis=1).max(axis=1)
            return tr.rolling(window=14).mean()

        return pd.Series([0] * len(data))

    def _extract_ta_period(self, indicator: str) -> int:
        match = re.search(r'(\d+)', indicator)
        return int(match.group(1)) if match else 14

    def execute_strategy(self, data: pd.DataFrame, code: str) -> List[Dict[str, Any]]:
        signals = []
        code = self._remove_comments(code)

        sma_pattern = r'ta\.sma\([^,]+,\s*(\d+)\)'
        ema_pattern = r'ta\.ema\([^,]+,\s*(\d+)\)'
        rsi_pattern = r'ta\.rsi\([^,]+,\s*(\d+)\)'

        for period_match in re.finditer(sma_pattern, code):
            period = int(period_match.group(1))
            sma = self.calculate_indicator(data, f'ta.sma(close, {period})')
            var_name = f'sma_{period}'
            self.context[var_name] = sma

        for period_match in re.finditer(ema_pattern, code):
            period = int(period_match.group(1))
            ema = self.calculate_indicator(data, f'ta.ema(close, {period})')
            var_name = f'ema_{period}'
            self.context[var_name] = ema

        for period_match in re.finditer(rsi_pattern, code):
            period = int(period_match.group(1))
            rsi = self.calculate_indicator(data, f'ta.rsi(close, {period})')
            var_name = f'rsi_{period}'
            self.context[var_name] = rsi

        crossover_pattern = r'ta\.crossover\(([^,]+),\s*([^)]+)\)'
        crossunder_pattern = r'ta\.crossunder\(([^,]+),\s*([^)]+)\)'

        for idx in range(len(data)):
            timestamp = int(data.index[idx].timestamp() * 1000)

            for match in re.finditer(crossover_pattern, code):
                series1 = match.group(1).strip()
                series2 = match.group(2).strip()

                val1_current = self._get_series_value(series1, idx)
                val2_current = self._get_series_value(series2, idx)
                val1_prev = self._get_series_value(series1, idx - 1) if idx > 0 else 0
                val2_prev = self._get_series_value(series2, idx - 1) if idx > 0 else 0

                if val1_prev <= val2_prev and val1_current > val2_current:
                    signals.append({
                        'timestamp': timestamp,
                        'side': 'BUY',
                        'price': data.iloc[idx]['close'],
                        'type': 'crossover'
                    })

            for match in re.finditer(crossunder_pattern, code):
                series1 = match.group(1).strip()
                series2 = match.group(2).strip()

                val1_current = self._get_series_value(series1, idx)
                val2_current = self._get_series_value(series2, idx)
                val1_prev = self._get_series_value(series1, idx - 1) if idx > 0 else 0
                val2_prev = self._get_series_value(series2, idx - 1) if idx > 0 else 0

                if val1_prev >= val2_prev and val1_current < val2_current:
                    signals.append({
                        'timestamp': timestamp,
                        'side': 'SELL',
                        'price': data.iloc[idx]['close'],
                        'type': 'crossunder'
                    })

        return signals

    def _get_series_value(self, series_expr: str, idx: int) -> float:
        series_expr = series_expr.strip()

        if series_expr in self.context and isinstance(self.context[series_expr], pd.Series):
            if 0 <= idx < len(self.context[series_expr]):
                return float(self.context[series_expr].iloc[idx])
            return 0.0

        if series_expr == 'close':
            return 0.0
        if series_expr == 'open':
            return 0.0
        if series_expr == 'high':
            return 0.0
        if series_expr == 'low':
            return 0.0

        return float(self.context.get(series_expr, 0))


class PineScriptStrategy:
    def __init__(self, pine_script: str, name: str = "PineScript"):
        self.name = name
        self.pine_script = pine_script
        self.parser = PineScriptParser()
        self.engine = None
        self.parsed = None

    def compile(self) -> bool:
        try:
            self.parsed = self.parser.parse(self.pine_script)
            self.engine = PineScriptEngine(self.parsed)
            logger.info(f"Pine Script compiled successfully: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to compile Pine Script: {e}")
            return False

    def generate_signals(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        if not self.engine:
            if not self.compile():
                return []

        try:
            return self.engine.execute_strategy(data, self.pine_script)
        except Exception as e:
            logger.error(f"Failed to generate signals: {e}")
            return []

    def get_indicators(self) -> Dict[str, pd.Series]:
        if not self.engine or not self.parsed:
            return {}

        indicators = {}
        for var_name, value in self.engine.context.items():
            if isinstance(value, pd.Series):
                indicators[var_name] = value

        return indicators
