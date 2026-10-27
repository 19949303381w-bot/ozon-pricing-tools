# lanyin Ozon Pricing Tools

离线售价与利润测算小工具。使用 Python 标准库 `decimal`，无需安装依赖，无网络请求，不读取账号、店铺、ERP 配置或任何商品文件。Python 3.9 及以上版本可运行。

在线版本：[lanyin Ozon 售价与利润计算器](https://lanyin.xyz/calculator/)。本工具与公开网页使用相同的固定成本、按售价计提费用与目标销售利润率公式，使用 Decimal 保留计算精度；显示时才保留两位小数。没有内置官方费率或实时汇率。

## 运行

下载并解压后，在本目录运行：

```shell
python -m ozon_pricing_tools --cost 25 --exchange 12 --sale-rub 1200 --domestic 3 --cross-border 15 --packing 1 --fulfilment 2 --commission 15 --advertising 5 --payment 1
```

以上全部数值仅作演算示例，**不是 Ozon 官方费率或当前汇率**。示例的固定成本为 46 元、折合销售收入 100 元、各项比例费用共 21 元、测算利润 33 元、销售利润率 33%。

按目标利润率反推售价：

```shell
python -m ozon_pricing_tools --mode reverse --cost 46 --exchange 12 --margin 30 --commission 15 --advertising 5 --payment 1
```

示例目标卢布售价显示为 `1126.53`。结果不是价格上传指令，不自动保存模板或更改店铺商品。实际刊登须由卖家在对应系统中核对并确认，平台审核结果另行确认。

## 输入与公式

`cost`、`domestic`、`cross-border`、`packing`、`fulfilment` 均为每件人民币成本。`exchange` 是每 1 人民币可兑换的卢布数量；`sale-rub` 是卢布售价。`commission`、`advertising`、`payment`、`margin` 按百分数填写，例如 `15` 表示 15%。目标 margin 是利润除以销售收入，不能当作采购成本加价率。

```text
固定成本 = 采购成本 + 国内运费 + 跨境运费 + 包材费用 + 末端履约费
人民币销售收入 = 卢布售价 ÷ 每人民币可兑换的卢布数
测算利润 = 人民币销售收入 × (1 − 佣金率 − 广告费率 − 支付费率) − 固定成本
测算销售利润率 = 测算利润 ÷ 人民币销售收入
目标卢布售价 = 固定成本 ÷ (1 − 费率合计 − 目标利润率) × 汇率
```

正向模式必须填写成本、正数汇率和售价；反推模式必须填写成本、正数汇率和目标利润率。可选固定费用和比例费用未填时按 0 处理，请自行核对所有实际成本，避免遗漏或重复计费。未填写的税费、退货、仓储和其他成本不在结果内。

零成本、零费用和零利润都是有效数值；负利润表示亏损，不改写为零。售价为 0 时销售利润率返回 JSON `null`。正向测算的费率合计达到或超过 100% 时仍可显示亏损，但不存在有限保本售价，`break_even_rub` 返回 `null`。反推时费率与目标利润率合计必须小于 100%。

成本、汇率及单项固定费用上限为 `1,000,000`；正向卢布售价上限为 `1,000,000,000`；各百分比输入为 0 至 100。主要结果金额绝对值不超过 `1,000,000,000,000`。无效值、无穷值、负数或不可达目标会明确报错。极小非零售价造成的极大负利润率可按科学计数法显示。命令成功返回退出码 0；缺失或无效输入返回 JSON `empty`/`error` 和退出码 2。

## 官方资料与费率核对

- [Ozon Global 官方帮助中心](https://docs.ozon.ru/global/)
- [Ozon Seller 官方教育中心](https://seller-edu.ozon.ru/)

费率应按自己店铺的实际类目、销售模式、价格段、物流线路、重量/尺寸、币种和生效日期核对。FBO、FBS、realFBS 与跨境线路不能混用。官方公开页面可能有登录或访问限制；本项目未核实任何“2026 最新官方佣金/物流费率”，因此不附具体官方数字表。请从官方适用规则或自己的实际账单取值，并把分段物流换算为该商品每件费用后填入。演算中的 15%、5%、1% 和汇率 12 均为示例。

## Python 调用与验证

```python
from ozon_pricing_tools import calculate

result = calculate(cost="25", exchange="12", sale_rub="1200", commission="15")
print(result.profit_cny)       # Decimal，保留计算精度
print(result.to_dict())       # JSON 兼容字典，金额显示为两位小数字符串
```

```shell
python -m unittest discover -s tests -v
```

本项目包含通用公式代码及独立回归测试，不包含 ERP 运行代码、凭据、店铺信息或任何平台私有数据。MIT 许可见 [LICENSE](LICENSE)。
