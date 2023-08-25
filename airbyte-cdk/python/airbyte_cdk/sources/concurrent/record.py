#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#
from airbyte_cdk.sources.concurrent.stream_partition import StreamPartition
from airbyte_cdk.sources.streams.core import StreamData


class Record:
    def __init__(self, stream_data: StreamData, stream_partition: StreamPartition):
        self.stream_data = stream_data
        self.stream_partition = stream_partition

    def __eq__(self, other):
        if not isinstance(other, Record):
            return False
        return self.stream_partition == other.stream_partition and self.stream_data == other.stream_data