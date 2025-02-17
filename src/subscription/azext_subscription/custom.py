# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
#
# Code generated by aaz-dev-tools
# --------------------------------------------------------------------------------------------

# pylint: disable=too-many-lines
# pylint: disable=too-many-statements, protected-access

from knack.log import get_logger
from azure.core.exceptions import HttpResponseError
from azure.cli.core.aaz import has_value
from .aaz.latest.account import Create

logger = get_logger(__name__)


def _get_object_id_by_spn(graph_client, spn):
    accounts = list(graph_client.service_principal_list(
        filter="servicePrincipalNames/any(c:c eq '{}')".format(spn)))
    if not accounts:
        logger.warning("Unable to find user with spn '%s'", spn)
        return None
    if len(accounts) > 1:
        logger.warning("Multiple service principals found with spn '%s'. "
                       "You can avoid this by specifying object id.", spn)
        return None
    return accounts[0]['id']


def _get_object_id_by_upn(graph_client, upn):
    accounts = list(graph_client.user_list(filter="userPrincipalName eq '{}'".format(upn)))
    if not accounts:
        logger.warning("Unable to find user with upn '%s'", upn)
        return None
    if len(accounts) > 1:
        logger.warning("Multiple users principals found with upn '%s'. "
                       "You can avoid this by specifying object id.", upn)
        return None
    return accounts[0]['id']


def _get_object_id_from_subscription(graph_client, subscription):
    if subscription['user']:
        if subscription['user']['type'] == 'user':
            return _get_object_id_by_upn(graph_client, subscription['user']['name'])
        if subscription['user']['type'] == 'servicePrincipal':
            return _get_object_id_by_spn(graph_client, subscription['user']['name'])
        logger.warning("Unknown user type '%s'", subscription['user']['type'])
    logger.warning('Current credentials are not from a user or service principal. '
                   'Azure Key Vault does not work with certificate credentials.')
    return None


def _get_object_id(graph_client, subscription=None, spn=None, upn=None):
    if spn:
        return _get_object_id_by_spn(graph_client, spn)
    if upn:
        return _get_object_id_by_upn(graph_client, upn)
    return _get_object_id_from_subscription(graph_client, subscription)


def _object_id_args_helper(cli_ctx, object_id=None, spn=None, upn=None):
    if not object_id:
        from azure.cli.command_modules.role import graph_client_factory
        graph_client = graph_client_factory(cli_ctx)
        object_id = _get_object_id(graph_client, spn=spn, upn=upn)
        if not object_id:
            raise HttpResponseError('Unable to get object id from principal name.')
    return object_id


class AccountCreate(Create):
    @classmethod
    def _build_arguments_schema(cls, *args, **kwargs):
        from azure.cli.core.aaz import AAZStrArg
        args_schema = super()._build_arguments_schema(*args, **kwargs)
        args_schema.owner_object_id = AAZStrArg(
            options=["--owner-object-id"],
            help="The object id(s) of the owner(s) which should be granted access to the new subscription."
        )
        args_schema.owner_spn = AAZStrArg(
            options=["--owner-spn"],
            help="The service principal name(s) of the owner(s) which should be granted access to the new subscription."
        )
        args_schema.owner_upn = AAZStrArg(
            options=["--owner-upn"],
            help="The user principal name(s) of owner(s) who should be granted access to the new subscription."
        )
        args_schema.offer_type._required = True
        args_schema.additional_parameters._registered = False
        args_schema.owners._registered = False
        return args_schema

    def pre_operations(self):
        args = self.ctx.args
        owner_object_id, owner_spn, owner_upn = [], [], []
        if has_value(args.owner_object_id):
            owner_object_id = [_object_id_args_helper(self.cli_ctx, object_id=x) for x
                               in args.owner_object_id.to_serialized_data().split(',')]
        if has_value(args.owner_spn):
            owner_spn = [_object_id_args_helper(self.cli_ctx, spn=x) for x
                         in args.owner_spn.to_serialized_data().split(',')]
        if has_value(args.owner_upn):
            owner_upn = [_object_id_args_helper(self.cli_ctx, upn=x) for x
                         in args.owner_upn.to_serialized_data().split(',') if has_value(args.owner_upn)]
        owners = owner_object_id + owner_spn + owner_upn
        args.owners = [{'object_id': x} for x in owners]
