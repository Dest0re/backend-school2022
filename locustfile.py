import logging
from datetime import datetime
from http import HTTPStatus

from locust import TaskSet, task, constant, HttpUser, SequentialTaskSet
from locust.exception import RescheduleTask

from megamarket.api.handlers import NodesView, NodeView, DeleteView
from megamarket.api.schema import DATETIME_FORMAT
from megamarket.utils.testing import generate_shop_units, url_for


class MegamarketTaskSet(SequentialTaskSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.round = 0
        self.dataset = self.make_dataset()

    @staticmethod
    def make_dataset():
        return generate_shop_units(count=1000, categories_count=100)

    def request(self, method, path, expected_status, **kwargs):
        with self.client.request(
            method, path, catch_response=True, **kwargs
        ) as response:
            if response.status_code != expected_status:
                response.failure(
                    f'Expected status {expected_status}, got {response.status_code}'
                )

                logging.info(
                    'round %r: %s %s, http status %d (expected %d), took %rs',
                    self.round, method, path, response.status_code, expected_status,
                    response.elapsed.total_seconds()
                )
            return response

    def create_import(self, dataset):
        resp = self.request('POST', '/imports', HTTPStatus.OK, json=dataset)

        if resp.status_code != HTTPStatus.OK:
            raise RescheduleTask

        return resp['data']

    def get_unit(self, unit_id):
        url = url_for(NodesView.URL_PATH, id=unit_id)
        return self.request('GET', url, HTTPStatus.OK,
                            name='/nodes/{id}')

    def get_sales(self, date):
        return self.request('GET', '/sales', HTTPStatus.OK,
                            params={'date': date})

    def get_node_statistics(self, node_id):
        url = url_for(NodeView.URL_PATH, id=node_id)
        return self.request('GET', url, HTTPStatus.OK)

    def delete_node(self, node_id):
        url = url_for(DeleteView.URL_PATH, id=node_id)
        return self.request('DELETE', url, HTTPStatus.OK)

    @task
    def create_import_task(self):
        self.create_import(self.dataset)

    @task
    def get_unit_task(self):
        self.get_unit(self.dataset[0]['id'])

    @task
    def get_sales_task(self):
        self.get_sales(datetime.now().strftime(DATETIME_FORMAT))

    @task
    def get_node_statistics_task(self):
        self.get_node_statistics(self.dataset[0]['id'])

    @task
    def delete_node_task(self):
        self.delete_node(self.dataset[0]['id'])

    # @task
    # def workflow(self):
    #     self.round += 1
    #     dataset = self.make_dataset()
    #
    #     self.create_import(dataset)
    #     self.get_unit(dataset[0]['id'])
    #     self.get_sales(datetime.now().strftime(DATETIME_FORMAT))
    #     self.get_node_statistics(dataset[0]['id'])
    #     self.delete_node(dataset[0]['id'])


class WebsiteUser(HttpUser):
    tasks = [MegamarketTaskSet]
    wait_time = constant(1)


