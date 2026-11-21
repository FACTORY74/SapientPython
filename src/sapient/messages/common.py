"""Common inner messages used by several SAPIENT outer messages."""

from sapient_msg.bsi_flex_335_v2_0.associated_detection_pb2 import (
    AssociatedDetection,
    AssociationRelation,
)
from sapient_msg.bsi_flex_335_v2_0.associated_file_pb2 import AssociatedFile
from sapient_msg.bsi_flex_335_v2_0.follow_pb2 import FollowObject

__all__ = [
    "AssociatedDetection",
    "AssociatedFile",
    "AssociationRelation",
    "FollowObject",
]
