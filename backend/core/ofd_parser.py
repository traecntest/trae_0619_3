# -*- coding: utf-8 -*-
import zipfile
import os
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from io import BytesIO

from lxml import etree

from backend.core.logging_config import logger


class OFDParser:
    def __init__(self):
        self.ns = {
            'ofd': 'http://www.ofdspec.org/2016',
        }

    def parse(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"开始解析OFD文件: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"OFD文件不存在: {file_path}")

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                ofd_content = self._read_zf_file(zf, 'OFD.xml')
                if not ofd_content:
                    raise ValueError("OFD.xml 文件不存在")

                ofd_root = etree.fromstring(ofd_content)
                doc_body = ofd_root.find('.//ofd:DocBody', self.ns)
                if doc_body is None:
                    raise ValueError("未找到 DocBody 节点")

                doc_root_elem = doc_body.find('ofd:DocRoot', self.ns)
                if doc_root_elem is None:
                    raise ValueError("未找到 DocRoot 节点")

                doc_root_path = doc_root_elem.text
                doc_dir = os.path.dirname(doc_root_path) if '/' in doc_root_path else ''

                doc_content = self._read_zf_file(zf, doc_root_path)
                if not doc_content:
                    raise ValueError(f"文档根文件不存在: {doc_root_path}")

                result = self._parse_document(doc_content, zf, doc_dir)
                result['file_name'] = os.path.basename(file_path)
                result['file_type'] = 'ofd'

                logger.info(f"OFD文件解析完成: {file_path}")
                return result

        except Exception as e:
            logger.error(f"OFD文件解析失败: {file_path}, error={e}")
            raise

    def _read_zf_file(self, zf: zipfile.ZipFile, path: str) -> Optional[bytes]:
        try:
            return zf.read(path)
        except KeyError:
            try:
                return zf.read(path.lstrip('/'))
            except KeyError:
                return None

    def _parse_document(self, doc_xml: bytes, zf: zipfile.ZipFile, doc_dir: str) -> Dict[str, Any]:
        root = etree.fromstring(doc_xml)
        common_data = root.find('.//ofd:CommonData', self.ns)

        result = {
            'success': True,
            'invoice_code': '',
            'invoice_number': '',
            'invoice_date': None,
            'check_code': '',
            'invoice_type': 'other',
            'seller_name': '',
            'seller_tax_id': '',
            'seller_address': '',
            'seller_bank': '',
            'buyer_name': '',
            'buyer_tax_id': '',
            'buyer_address': '',
            'buyer_bank': '',
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0'),
            'total_amount_with_tax': Decimal('0'),
            'remark': '',
            'payee': '',
            'reviewer': '',
            'drawer': '',
            'items': [],
        }

        tpl_infos = root.findall('.//ofd:Tpls/ofd:Tpl', self.ns)
        for tpl in tpl_infos:
            tpl_id = tpl.get('ID')
            tpl_name = tpl.get('Name', '')

        pages = root.findall('.//ofd:Pages/ofd:Page', self.ns)
        if pages:
            page_path = pages[0].get('BaseLoc')
            if page_path:
                full_path = os.path.join(doc_dir, page_path).replace('\\', '/')
                page_content = self._read_zf_file(zf, full_path)
                if page_content:
                    page_result = self._parse_page(page_content)
                    result.update(page_result)

        return result

    def _parse_page(self, page_xml: bytes) -> Dict[str, Any]:
        result = {
            'items': [],
        }

        try:
            root = etree.fromstring(page_xml)

            text_objs = root.findall('.//ofd:TextObject', self.ns)
            text_data = []
            for text_obj in text_objs:
                boundary = text_obj.get('Boundary', '0 0 0 0')
                parts = boundary.split()
                if len(parts) >= 4:
                    x, y = float(parts[0]), float(parts[1])
                else:
                    x, y = 0, 0

                text_content = text_obj.find('ofd:TextCode', self.ns)
                if text_content is not None and text_content.text:
                    text_data.append({
                        'text': text_content.text.strip(),
                        'x': x,
                        'y': y,
                    })

            text_data.sort(key=lambda t: (t['y'], t['x']))

            result = self._extract_invoice_info(text_data)

        except Exception as e:
            logger.warning(f"解析OFD页面内容失败: {e}")

        return result

    def _extract_invoice_info(self, text_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        result = {
            'invoice_code': '',
            'invoice_number': '',
            'invoice_date': None,
            'check_code': '',
            'seller_name': '',
            'seller_tax_id': '',
            'buyer_name': '',
            'buyer_tax_id': '',
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0'),
            'total_amount_with_tax': Decimal('0'),
            'items': [],
        }

        all_text = '\n'.join(t['text'] for t in text_lines)

        import re

        code_match = re.search(r'发票代码[：:]\s*(\d{10,12})', all_text)
        if code_match:
            result['invoice_code'] = code_match.group(1)

        number_match = re.search(r'发票号码[：:]\s*(\d{8,10})', all_text)
        if number_match:
            result['invoice_number'] = number_match.group(1)

        date_match = re.search(r'开票日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2})', all_text)
        if date_match:
            date_str = date_match.group(1)
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            try:
                result['invoice_date'] = datetime.strptime(date_str, '%Y-%m-%d').isoformat()
            except ValueError:
                pass

        check_match = re.search(r'校\s*验\s*码[：:]\s*([\d\s]+)', all_text)
        if check_match:
            result['check_code'] = check_match.group(1).replace(' ', '')

        seller_match = re.search(r'名\s*称[：:]\s*(\S+)', all_text)
        if seller_match:
            result['seller_name'] = seller_match.group(1)

        seller_tax_match = re.search(r'纳税人识别号[：:]\s*([0-9A-Z]{15,20})', all_text)
        if seller_tax_match:
            result['seller_tax_id'] = seller_tax_match.group(1)

        total_match = re.search(r'价税合计[（(]大写[)）][：:]?\s*[^\d]*([\d,.]+)\s*元', all_text)
        if total_match:
            try:
                result['total_amount_with_tax'] = Decimal(total_match.group(1).replace(',', ''))
            except Exception:
                pass

        amount_match = re.search(r'合\s*计[：:].*?([\d,.]+).*?([\d,.]+)', all_text)
        if amount_match:
            try:
                result['total_amount'] = Decimal(amount_match.group(1).replace(',', ''))
                result['total_tax'] = Decimal(amount_match.group(2).replace(',', ''))
            except Exception:
                pass

        return result


ofd_parser = OFDParser()


def parse_ofd_file(file_path: str) -> Dict[str, Any]:
    return ofd_parser.parse(file_path)
