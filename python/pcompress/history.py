import dataset
from .metadata import ChainMetadata
from .utils import fetch_cached_file

class History:
    def __init__(self, url: str = "http://chains.mggg.org.s3-website-us-east-1.amazonaws.com/"):
        if not url.endswith("/"):
            url += "/"
        self.url = url

        fetch_cached_file(self.url + "chains.db", "/tmp/chains.db")

        self.db = dataset.connect('sqlite:////tmp/chains.db')
        self.chains = self.db["chains"]
    
    def search(self, **kwargs):
        for result in self.chains.find(**kwargs):
            metadata = ChainMetadata(**result)
            metadata.url = self.url
            yield metadata

    def search_one(self, **kwargs):
        result = self.chains.find_one(**kwargs)
        if result:
            metadata = ChainMetadata(**result)
            metadata.url = self.url
            return metadata