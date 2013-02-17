# This file is part of PyTradeLib.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLib is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLib is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLib.  If not, see http://www.gnu.org/licenses/

import datetime
import calendar

from pytradelib import utils
from pytradelib import bar
from pytradelib import settings


class YahooFrequencyProvider(object):
    def __init__(self):
        self.__columns = ['DateTime', 'Close', 'High', 'Low', 'Open', 'Volume']

    def get_csv_column_labels(self):
        return ','.join(self.__columns)

    def row_to_bar(self, row):
        row = row.split(',')
        try:
            date = datetime.datetime.fromtimestamp(int(row[0]))
        except ValueError:
            date = datetime.datetime.strptime(row[0], settings.DATE_FORMAT)
        close = float(row[1])
        high = float(row[2])
        low = float(row[3])
        open_ = float(row[4])
        volume = float(row[5])
        try:
            return bar.Bar(date, open_, high, low, close, volume, close)
        except AssertionError, e:
            return str(e)

    def bar_to_row(self, bar_):
        ret = ','.join([
            '%i' % calendar.timegm(bar_.get_date_time().timetuple()),
            '%.2f' % bar_.get_close(),
            '%.2f' % bar_.get_high(),
            '%.2f' % bar_.get_low(),
            '%.2f' % bar_.get_open(),
            '%i' % bar_.get_volume()
            ])
        return ret

    @utils.lower
    def get_url(self, symbol, frequency, from_date=None):
        raise NotImplementedError("Hint: Use Firebug in places where you "\
            "might expect AJAX calls for intraday data. Implement at your own"\
            " risk; I'm not entirely sure what Yahoo's TOS are for using it.")

    def process_downloaded_data(self, data_file_paths):
        # minutely data has a big, multi-row header, and only comes one day at a time
        # times are formatted in seconds from the unix epoch; convert them to datetime
        for data, file_path in data_file_paths:
            symbol = utils.symbol_from_file_path(file_path)
            data_rows = data.strip().split('\n')
            # grab the column labels from the middle of the header and find the start index of the data
            error = False
            for i, row in enumerate(data_rows):
                if row.startswith('error'):
                    error = True
                    print 'error downloading minute data for %s: %s' % (
                        symbol, data_rows[i+1][len('message:'):])
                elif row.startswith('volume'):
                    # chop off the entire header so data_rows contains only bar rows
                    data_rows = data_rows[i+1:]
                    break
            if error:
                continue # FIXME: add to FailedSymbols?

            # date conversions
            # FIXME: store in UTC
            # FIXME: round bars to even minutes?
            # FIXME: add "fake" missing bars?
            #        maybe OHLC == avg prev/next closes and volume == None ?
            try:
                for i, row in enumerate(data_rows):
                    columns = row.split(',')
                    dt = datetime.datetime.fromtimestamp(int(columns[0]))
                    columns[0] = dt.strftime(settings.DATE_FORMAT)
                    data_rows[i] = ','.join(columns)
            except Exception, e:
                print 'error converting date for %s: %s' % (symbol, str(e))
                continue # FIXME: add to FailedSymbols?

            now = datetime.datetime.now().time() # FIXME: UTC
            if len(data_rows) > 1 \
              and (datetime.time(9, 30) < now < datetime.time(16)):
                # FIXME: emit this bar
                latest_quote = data_rows.pop(-1)
            yield (data_rows, file_path)