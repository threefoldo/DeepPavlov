"""
Copyright 2017 Neural Networks and Deep Learning lab, MIPT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sqlite3
from typing import List, Any, Dict, Optional, Generator, Tuple

from deeppavlov.core.common.log import get_logger
from deeppavlov.core.common.registry import register
from deeppavlov.core.data.utils import download
from deeppavlov.core.commands.utils import expand_path, is_empty

logger = get_logger(__name__)

DB_URL = 'http://lnsigo.mipt.ru/export/datasets/wikipedia/wiki_full.db'


@register('sqlite_iterator')
class SQLiteDataIterator:
    """
    Load a SQLite database, read data batches and get docs content.
    """
    def __init__(self, data_path: str='', data_url: str=DB_URL, batch_size: int=None, **kwargs):
        """
        :param load_path: a path to a SQLite database
        :param batch_size: a batch size for reading from the database
        """
        download_path = expand_path(data_path)
        if not download_path.exists() or is_empty(download_path):
            logger.info('[downloading wiki.db from {} to {}]'.format(data_url, download_path))
            download_path = download_path.joinpath(data_url.split("/")[-1].split(".")[0])
            download(download_path, data_url)

        self.load_path = download_path
        self.connect = sqlite3.connect(str(self.load_path), check_same_thread=False)
        self.db_name = self.get_db_name()
        self.doc_ids = self.get_doc_ids()
        self.doc2index = self.map_doc2idx()
        self.batch_size = batch_size

    def get_doc_ids(self) -> List[Any]:
        cursor = self.connect.cursor()
        cursor.execute('SELECT id FROM {}'.format(self.db_name))
        ids = [ids[0] for ids in cursor.fetchall()]
        cursor.close()
        return ids

    def get_db_name(self) -> str:
        cursor = self.connect.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        assert cursor.arraysize == 1
        name = cursor.fetchmany(0)[0][0]
        cursor.close()
        return name

    def map_doc2idx(self) -> Dict[int, Any]:
        doc2idx = {doc_id: i for i, doc_id in enumerate(self.doc_ids)}
        print("The size of database is {} documents".format(len(doc2idx)))
        return doc2idx

    def get_doc_content(self, doc_id: Any) -> Optional[str]:
        cursor = self.connect.cursor()
        cursor.execute(
            "SELECT text FROM documents WHERE id = ?",
            (doc_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result if result is None else result[0]

    def read_batch(self, batch_size=1000) -> Generator[Tuple[List[str], list], Any, None]:
        _batch_size = self.batch_size or batch_size
        batches = [self.doc_ids[i:i + _batch_size] for i in
                   range(0, len(self.doc_ids), _batch_size)]
        # DEBUG
        # len_batches = len(batches)

        for i, doc_ids in enumerate(batches):
            # DEBUG
            # logger.info(
            #     "Processing batch # {} of {} ({} documents)".format(i, len_batches, len(doc_ids)))
            docs = [self.get_doc_content(doc_id) for doc_id in doc_ids]
            yield docs, doc_ids
