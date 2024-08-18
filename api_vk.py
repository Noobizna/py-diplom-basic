import requests
from tqdm import tqdm


def token_id(file_name):
    """
    The function gets the token and ID from the file

    Args:
        file_name (str): the path to the file containing the token and ID on separate lines

    Return:
        list: a list containing the token and ID
    """
    with open(file_name, 'r') as file:
        token, ident = file.readline().strip(), file.readline().strip()
    return [token, ident]


def max_size(dict_photo):
    """
    The function for finding the url of photos with the maximum area

    Args:
        dict_photo(list): a list of dictionaries containing information about photos

    Return:
        tuple: the url of the photos with the maximum area and the type of photos
    """
    if not dict_photo:
        return None
    maxim_size = 0
    element = -1
    for number in range(len(dict_photo)):
        extent = dict_photo[number].get('width') * dict_photo[number].get('height')
        if extent > maxim_size:
            maxim_size = extent
            element = number
    if element != -1:
        return dict_photo[element].get('url'), dict_photo[element].get('type')
    else:
        return None


class VK:
    """
    The class for interacting with the vk api

    Attributes:
        token (str): the access token that is used when making requests to the server
        id (str): the ID of the VK user whose photos will be used for uploading
        version (str): version of api vk
        params (dict): parameters for api requests
        json (dict): received json response when extracting photos
        export_dict (dict): dictionary with exported photos
    """
    def __init__(self, token_list, version='5.131'):
        """
        Function for initializing the vk class

        Args:
            token_list (list): a list containing the token and user ID
            version (str): api version, default "5.131"
        """
        self.token = token_list[0]
        self.id = token_list[1]
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self.extract_photo()

    def users_info(self):
        """
        The function receives information about the user

        Return:
           response (dict): a json response from the api containing information about the user
        """
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()

    def get_photo_info(self):
        """
        The function receives information about the user's photos

        Return:
             photo_info['count'] (int): the number of photos
             photo_info['items'] (list): the list of photos
        """
        url = 'https://api.vk.com/method/photos.get/'

        params = {'owner_id': self.id,
                  'album_id': 'profile',
                  'extended': 1,
                  'photo_sizes': 1,
                  }
        photo_info = requests.get(url, params={**self.params, **params}).json()['response']
        return photo_info['count'], photo_info['items']

    def pars_photo(self):
        """
        A function for parsing photos and grouping them by the number of likes

        Return:
            result (dict): a dictionary where the keys are the number of likes,
            and the values are information about photos
        """
        result = {}
        photo_count, photo_items = self.get_photo_info()
        for count in range(photo_count):
            likes_count = photo_items[count]['likes']['count']
            photo_url, photo_size = max_size(photo_items[count]['sizes'])
            value = result.get(likes_count, [])
            value.append({
                "file_name": likes_count,
                "size": photo_size,
                "url": photo_url
                })
            result[likes_count] = value
        return result

    def extract_photo(self):
        """
        The function extracts photos and returns information about them

        Return:
            json_list (list): List of photos
            json_dict (dict): Dictionary with photo urls
        """
        json_dict = {}
        json_list = []
        photo_dict = self.pars_photo()
        for element in photo_dict.keys():
            for key in photo_dict[element]:
                if len(photo_dict[element]) == 1:
                    file_name = f'{element}.jpg'
                else:
                    file_name = f'{element} {key['file_name']}.jpg'
                json_list.append({'file_name': file_name, 'size': key['size']})
                json_dict[file_name] = photo_dict[element][0]['url']
        return json_list, json_dict


class YandexDisk:
    """
    A class for interacting with Yandex Disk API

    Attributes:
        url (str): The base URL for requests to Yandex Disk
        headers (dict): Headers for requests to the Yandex Disk API
        folder_name (str): The name of the folder on Yandex Disk
    """
    def __init__(self, token, folder_name):
        """
        The initialization function of the YandexDisk class

        Args:
            token (str): the access token that is used when making requests to the server
            folder_name (str): the name of the folder on Yandex Disk
        """
        self.url = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'OAuth {token}'
        }
        self.folder_name = folder_name

    def create_folder(self, folder_name):
        """
        A function for creating a folder on Yandex Disk if it does not exist

        Args:
            folder_name (str): the name of the folder on Yandex Disk

        Return:
            folder_name (str): the name of the folder on Yandex Disk
        """
        params = {'path': folder_name}
        response = requests.get(self.url, headers=self.headers, params=params)
        if response.status_code == 404:
            response = requests.put(self.url, headers=self.headers, params=params)
            if response.status_code == 201:
                print('Папка успешно создана')
            else:
                print(f'Ошибка создания папки: {response.json()}')
        elif response.status_code == 200:
            print('Папка уже существует')
        else:
            print(f'Ошибка при проверке существования папки: {response.json()}')

        return folder_name

    def folder_rec(self, folder_name):
        """
        The function gets a list of files in the specified folder

        Args:
            folder_name (str): the name of the folder on Yandex Disk

        Return:
            list: list of file names in the folder
        """
        url = self.url
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            items = response.json().get('_embedded', {}).get('items', [])
            folder_list = [item['name'] for item in items]
            return folder_list
        else:
            print(f'Ошибка при получении списка содержимого папки: {response.json()}')
            return []

    def fill_folder(self, dict_files):
        """
        The function uploads files to the specified folder

        Args:
            dict_files (dict): the dictionary maps the keys (file names) to the corresponding URLs

        Return:
            None
            Prints the number of photos added and operation statuses
        """
        files_in_folder = self.folder_rec(self.folder_name)
        count = 0
        for key, url in tqdm(dict_files.items(), desc="Uploading files", unit="file"):
            if key not in files_in_folder:
                params = {'path': f'{self.folder_name}/{key}', 'url': url, 'overwrite': 'true'}
                response = requests.post(f'{self.url}/upload', headers=self.headers, params=params)
                if response.status_code == 202:
                    print(f'Фото {key} успешно добавлено!')
                    count += 1
                else:
                    print(f'Ошибка при добавлении фото {key}: {response.json()}')
            else:
                print(f'Файл по ключу {key} уже существует!')
        print(f'Добавлено {count} фотографий')


token_vk = 'token_id_vk.txt'
vk = VK(token_id(token_vk))
print(vk.extract_photo()[1])
print(vk.json)
token_yandex = 'token_ya.txt'
yandex = YandexDisk(token_id(token_yandex)[0], 'vk_photos')
yandex.fill_folder(vk.export_dict)
