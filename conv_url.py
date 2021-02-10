from urllib.parse import unquote
import json


class DecodeURIComponent:
    """
    parser from  url
    """
    def __init__(self, data:str):
        self.source = data

    def to_dict(self)->dict:
        json_source= self._get_json_source()
        return self._get_dict(json_source)

    def _get_json_source(self):
        return json.loads(unquote(self.source))

    def _get_dict(self, data:list) ->dict:
        result = dict()
        if len(data)==0:
            return result
        if type(data[0])==list:
            return self._parse_array_to_dict(data)

        for i,k in zip(data[0::2], data[1::2]):
            if type(k)==list:
                result[i]=self._get_dict(k)
            else:
                result[i]=k
        return result

    def _parse_array_to_dict(self, data:list)->dict:
        result = dict()
        num =0
        for target_list in data:
           result[num] =  self._get_dict(target_list)
           num = num+1
        return result