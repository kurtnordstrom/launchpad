from datetime import datetime
import pymarc
import re
from PyZ3950 import zoom


class Z3950Catalog():

    def __init__(self, ip, port, name, syntax):
        self.ip = ip
        self.port = port
        self.name = name
        self.syntax = syntax
        self.conn = self._getconn(ip, port, name, syntax)

    def _getconn(self, ip, port, name, syntax):
        conn = zoom.Connection(ip, port)
        conn.databaseName = name
        conn.preferredRecordSyntax = syntax
        return conn

    def zoom_record(self, bibid):
        query = zoom.Query('PQF', '@attr 1=12 %s' % bibid.encode('utf-8'))
        try:
            results = self.conn.search(query)
            if len(results) > 0:
                return results[0]
        except:
            raise

    def get_holding(self, bibid=None, zoom_record=None, school=''):
        holdings = []
        if bibid and not zoom_record:
            zoom_record = self.zoom_record(bibid)
        if hasattr(zoom_record, 'data') and hasattr(zoom_record.data,
                                                    'holdingsData'):
            for rec in zoom_record.data.holdingsData:
                holdmeta = {}
                holdmeta['item_status'] = 0
                holdmeta['callnum'] = ''
                holdmeta['status'] = ''
                holdmeta['url'] = ''
                holdmeta['note'] = ''
                holdmeta['msg'] = ''
                if hasattr(rec[1], 'callNumber'):
                    holdmeta['callnum'] = rec[1].callNumber.rstrip('\x00')
                else:
                    holdmeta['callnum'] = ''
                holdmeta['location'] = rec[1].localLocation.rstrip('\x00')
                if hasattr(rec[1], 'publicNote') and school == 'GT':
                    status = rec[1].publicNote.rstrip('\x00')
                    holdmeta['status'] = self.append_leading_year_digits(
                        status)
                if hasattr(rec[1], 'publicNote') and school == 'GM':
                    holdmeta['note'] = rec[1].publicNote.rstrip('\x00')
                if hasattr(rec[1], 'circulationData'):
                    holdmeta['status'] = rec[1].circulationData[0].availableNow
                if holdmeta['status'] is True or\
                        holdmeta['status'].strip() == 'AVAILABLE':
                    holdmeta['status'] = 'Not Charged'
                    holdmeta['item_status'] = 1
                elif holdmeta['status'] is False or\
                        holdmeta['status'] == ' DUE':
                    if rec[1].circulationData[0].availablityDate:
                        date_obj = datetime.strptime(rec[1].circulationData[0]
                                                     .availablityDate,
                                                     '%Y-%m-%d %H:%M:%S')
                        holdmeta['status'] = date_obj.strftime("DUE %m-%d-%Y")
                        holdmeta['item_status'] = 0
                    else:
                        holdmeta['status'] = 'Charged'
                        holdmeta['item_status'] = 0
                marc = pymarc.record.Record(zoom_record.data.
                                            bibliographicRecord.encoding[1])
                if marc['856']:
                    if 'www.loc.gov' not in marc['856']['u']:
                        holdmeta['url'] = marc['856']['u']
                        holdmeta['msg'] = marc['856']['z']
                holdings.append(holdmeta)
            return holdings
        if hasattr(zoom_record, 'data'):
            marc = pymarc.record.Record(zoom_record.data)
            if marc['856']:
                holdmeta = {}
                holdmeta['url'] = marc['856']['u']
                holdmeta['msg'] = marc['856']['z']
                holdmeta['callnum'] = ''
                holdmeta['status'] = ''
                holdmeta['note'] = ''
                holdmeta['item_status'] = 0
                holdmeta['location'] = ''
                holdings.append(holdmeta)
                return holdings
            else:
                return [{'item_status': 0, 'location': '', 'callnum': '',
                        'status': '', 'url': '', 'note': '', 'msg': ''}]
        return [{'item_status': 0, 'location': '', 'callnum': '', 'status': '',
                 'url': '', 'note': '', 'msg': ''}]

    def append_leading_year_digits(self, status):
        if len(status) > 4:
            result = re.match('(\d{2})[/.-](\d{2})[/.-](\d{2})$', status[4:])
            if result:
                return status[:10] + '20' + status[10:]
        return status
