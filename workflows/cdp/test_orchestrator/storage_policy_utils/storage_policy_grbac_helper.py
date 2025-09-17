"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: shubham.shrivastava@nutanix.com.

This module contains workflows to test Storage Policy GRBAC.
"""
#pylint: disable=no-member, too-many-locals, too-many-branches, bare-except
#pylint: disable=too-many-statements, too-many-return-statements,
#pylint: disable=protected-access
import functools
import random
import time
import traceback

from framework.entities.storage_policy.storage_policy import \
  StoragePolicy
from framework.entities.v4_sdk.category.categories import Categories
from framework.exceptions.interface_error import NuTestPrismError
from framework.exceptions.nutest_error import NuTestError
from framework.lib.nulog import DEBUG, ERROR, INFO, STEP

from workflows.cdp.rbac.lib.grbac import GRBAC

def validate_operation(req_permissions=None):
  """
  Decorator to validate the operation based on the permissions.
  Args:
    req_permissions(list): Permissions required to perform the operation.
                      If not provided, it will be an empty list indicating that
                      no permission is required.
  Returns:
    (func): Wrapped function.
  Raises:
    (NuTestError): If GRBAC Helper is not defined in the test object.
  """
  def validate_operation_outer(func):
    """
    Outer wrapper.
    Args:
      (func): Function to be executed.
    Returns:
      (func): Wrapped function.
    """
    @functools.wraps(func)
    def wrapper(self, user, *args, **kwargs):
      """
      This method validates the operation based on the permissions.
      Args:
        self(obj): Caller Object.
        user(str): Username.
      Kwargs:
        entity_id(str): Entity ext_id for entity specific operations.
        is_entity_self_owned(bool): If True, indicates operation with
                                    self-owned entity is performed.
        category_id(str): Category ext_id. For SP operations with category.
      Returns:
        (tuple): (True, "") if operation is authorised.
                 (False, ERR_MSG) if operation is not authorised.
      """
      if not hasattr(self, "grbac_helper"):
        raise NuTestError("GRBAC Helper not defined in the test object.")

      entity_id = kwargs.get('entity_id')
      # While calling the function, user needs to provide is_entity_self_owned
      # This ensures that the entity under test is self-owned or not.
      is_entity_self_owned = kwargs.get("is_entity_self_owned", False)
      is_dsp = False
      # Assigning a copy of the list to avoid modification of the original list.
      required_permissions = req_permissions[:] or []

      try:
        # verifying that user is assigned to a role.
        self.grbac_helper.user_accessible_entities(user)
        DEBUG("User is assigned to a role.")
        is_op_allowed = True
      except NuTestError as err:
        if "not assigned to any role" not in str(err):
          ERROR(f"Received unexpected error: {err}")
          return False, str(err)
        DEBUG(f"User is not assigned to any role, error: {err}")
        is_op_allowed = False
        # If user is not assigned to any role.
        excepted_status_codes = [422]

      # If the user is assigned to a role, we will be checking if the user
      # has the required permissions to perform the operation.
      # If the user has sufficient permissions, we will be checking for the
      # scenarios when user will lose the permission and operation won't be
      # allowed and update the expected_status_codes accordingly.
      if is_op_allowed:
        # If the entity has category attached, user will require to have
        # CATEGORY_VIEW permission to perform DELETE, UPDATE.
        if entity_id and func.__name__ != "verify_sp_get":
          sp = StoragePolicy.list(self.pc_cluster, interface_type="SDK",
                                  filterby=f"extId eq '{entity_id}'")[0]
          # If SP has an SP already associated, we will require to check if
          # user has the required permissions for category too.
          existing_cat = sp.model.category_ext_ids[0] \
            if sp.model.category_ext_ids else None
          # If category is associated, we will be updating the kwargs with it.
          if existing_cat:
            kwargs["category_id"] = existing_cat
          # User will require to have Category VIEW permission to delete SP
          # in case SP is associated with category.
          if kwargs.get("category_id"):
            required_permissions.append("View_Category")
          # Updating if SP is DSP.
          if sp.name == "Default-Storage":
            is_dsp = True

        # For category included Create/ Update operations, we need to have
        # View_Category permission.
        if func.__name__ in ("verify_sp_create", "verify_sp_update") and \
          kwargs.get("category_id"):
          required_permissions.append("View_Category")
        # Checking if user has the required permissions.
        user_permissions = self.grbac_helper.get_user_permissions(user)
        DEBUG(f"{user} permissions: {user_permissions}; required permissions:"
              f"{required_permissions}.")
        is_op_allowed = set(required_permissions).issubset(user_permissions)
        DEBUG(f"{user} has required permissions: {is_op_allowed}.")

        # Default-Storage SP should not get updated or deleted regardless of the
        # permissions.
        if func.__name__ in ("verify_sp_update", "verify_sp_delete") and is_dsp:
          is_op_allowed = False

        if is_op_allowed and func.__name__ == "verify_sp_create":
          is_op_allowed = self._is_creation_allowed(user)
        # If user has the required permissions, we will be checking if the user
        # has the required scope to perform the operation.
        if is_op_allowed:
          excepted_status_codes = \
            self.get_expected_status_code(user, entity_id, is_entity_self_owned,
                                          kwargs.get("category_id"))
        else:
          DEBUG("User does not have permission to perform the operation.")
          excepted_status_codes = [403]

      try:
        STEP(f"{func.__name__.upper()} Expecting: {excepted_status_codes}")
        result = func(self, user, *args, **kwargs)
        DEBUG(f"Op Call result: {result}.")
        if isinstance(result, tuple) and result[0] is False:
          return result
        if 200 not in excepted_status_codes:
          err = "User without permission, is able to perform the operation."
          ERROR(err)
          return False, err
      except (NuTestPrismError, NuTestError):
        result = self._is_operation_unauthorised(user, excepted_status_codes)
        DEBUG(f"_is_operation_unauthorised: {result}")
        return result
      except AssertionError as ae:
        # For verification methods (delete(validate=True)), we handle the
        # assertion error and return False.
        ERROR(f"AssertionError: {ae}: {traceback.format_exc()}")
        return False, str(ae)
      except:
        # For any other unhandled error.
        err = f"Received error unhandled Error: {traceback.format_exc()}"
        ERROR(err)
        return False, str(err)
      DEBUG("Operation is authorised.")
      return True, ""
    return wrapper
  return validate_operation_outer

class StoragePolicyGRBACHelper:
  """
  This class contains methods for grbac workflow for V4.X and above.
  """

  def __init__(self, test_obj, test_args):
    """
    Initialize method for volume group grbac helper.
    Args:
      test_obj(obj): Test object.
      test_args(dict): Test args.
    """
    self.resources = test_obj.resources
    self.grbac_helper = GRBAC(self.resources)
    self.pe_clusters = test_obj.get_resources_by_type(test_obj.NOS_CLUSTER)
    self.pc_clusters = test_obj.get_resources_by_type(test_obj.PRISM_CENTRAL)
    self.pc_cluster = self.pc_clusters[0]
    self.test_args = test_args
    # Setting the api version to v4.0 by default.
    self.api_version = test_args.get("api_version", "v4.0")

  @property
  def all_storage_policies(self):
    """
    All SPs at the instance.
    Returns:
      (dict): {SP_ENTITY_ID: SP_NAME} mapping.
    """
    all_sps = StoragePolicy.list(self.pc_clusters[0], interface_type="SDK",
                                 use_cache=False)
    return {sp.entity_id: sp.model.name for sp in all_sps}

  def get_expected_status_code(self, user, entity=None,
                               is_entity_self_owned=False, category_id=None):
    """
    This method returns the list of expected status code.
    Args:
      user(str): username.
      entity(str): uuid of the entity.
      is_entity_self_owned(bool): If True, entity is user created.
      category_id(str): Category ext_id.
    Returns:
      expected_status_code(list): Returns the list of expected
      http code depending upon the user permissions.
    """
    has_scope_sp_all = "ALL" in self.grbac_helper.user_accessible_entities(
      user, "storage_policy")
    has_scope_cat_all = "ALL" in self.grbac_helper.user_accessible_entities(
      user, "category")
    user_self_owned_status = self.grbac_helper.has_self_owned_acp(user)
    DEBUG(f"Calculating {user} scope for SP: {entity} with args: "
          f"SP scope ALL: {has_scope_sp_all}, Category scope ALL: "
          f"{has_scope_cat_all}, self-owned user: {user_self_owned_status}."
          f"Entity self-owned: {is_entity_self_owned},"
          f"Category: {category_id}.")

    user_accessible_entities = self.get_all_user_accessible_entities(user)

    # For category in request, the category has to be accessible to the user.
    if category_id:
      is_category_accessible_to_user = \
        category_id in user_accessible_entities["category"] \
          if category_id else True
      if not (is_category_accessible_to_user or has_scope_cat_all):
        DEBUG(f"{user} does not have permission to perform the operation,"
              f"as the category in request is not accessible to user.")
        return [403]

    # If user does not have permissions on entity, user should
    # be getting 403.
    if entity:
      is_entity_accessible_to_user = \
        entity in user_accessible_entities["storage_policy"]
      if not (has_scope_sp_all or
              (user_self_owned_status and is_entity_self_owned)
              or is_entity_accessible_to_user):
        DEBUG(f"User does not have permission to perform the operation,  "
              f"has_scope_all:{has_scope_sp_all}\n user_self_owned_status:"
              f"{user_self_owned_status}\n is_entity_self_owned:"
              f"{is_entity_self_owned}\n is_entity_accessible_to_user:"
              f"{is_entity_accessible_to_user}\n"
              f"has_scope_cat_all: {has_scope_cat_all}.")
        return [403]

    DEBUG("User has permission to perform the operation.")
    return [200, 202, 204]

  @validate_operation(["View_Storage_Policy"])
  def verify_sp_list(self, user, password, odata_list=None, pc_dashboard=None):
    """
    Method performs storage policies list operation, and verifies it.
    Args:
      user(str): Username with which list op to be performed and verified.
      password(str): Password.
      odata_list(list): List of odata params to be verified.
      pc_dashboard(obj): PC Dashboard object, if provided, will be used to
                         perform the list validation through UI.
    Returns:
      (tuple): (True, "") if listed storage policies are legal & all and
                  only scoped policies is listed (Assuming there has been no
                  storage policy created with the user).
               (False, ERR_MSG) if listed storage policies are either without
                  permission or listed storage policies are not adhering to the
                  scoped storage policies to the user.
    """
    if odata_list:
      STEP(f"Verifying oData support for SP list operation for user:{user}")
      # If any fails in the loop, the method will raise an exception which will
      # be caught in the decorator. Hence, we are not consolidating the results.
      for odata_params in odata_list:
        INFO(f"Verifying SP list operation with oData params: {odata_params}.")
        odata_response = StoragePolicy.list(
          self.pc_cluster, interface_type="SDK", username=user,
          password=password, use_cache=False,
          api_key=self.grbac_helper.user_api_key_mapping.get(user),
          **odata_params)
        DEBUG(f"{user} oData response for List for {odata_params}"
              f":{odata_response}")
      INFO(f"{user} successfully verified List oData.")
      return True, ""

    accessible_entities = (
      self.get_all_user_accessible_entities(user))["storage_policy"]
    STEP(f"Verifying SP-list operation for user: {user}")
    if pc_dashboard:
      # If pc_dashboard is passed, we will be using UI to verify the list.
      accessible_entities_names = [sp_name for sp_ext_id, sp_name in self.all_storage_policies.items()
                                   if sp_ext_id in accessible_entities]
      storage_policies = pc_dashboard.storage.storage_policies
      storage_policies.verify_sp_list(set(accessible_entities_names))
    else:
      storage_policies = StoragePolicy.list(
        self.pc_cluster, interface_type="SDK", username=user,
        password=password, use_cache=False,
        api_key=self.grbac_helper.user_api_key_mapping.get(user))
      storage_policies = [sp.entity_id for sp in storage_policies]
      DEBUG(f"Listed storage policies for {user} user:{storage_policies}")

      if set(storage_policies) != set(accessible_entities):
        err_msg = (
          f"Listed storage policies for user, {user}, is not adhering the scoped "
          f"storage policies. Scoped and expected SPs: {accessible_entities},\n"
          f"Actual SPs: {storage_policies}.")
        ERROR(err_msg)
        return False, err_msg
    INFO(f"{user} successfully listed scoped storage policies.")
    return True, ""

  @validate_operation(["View_Storage_Policy"])
  def verify_sp_get(self, user, password, **kwargs):
    """
    Method performs storage policies list operation, and verifies it.
    Args:
      user(str): User with which list op to be performed and verified.
      password(str): Password.
    Kwargs:
      entity_id(str): Entity ID.
              Note: Having entity_id in kwargs is mandatory, we are having it in
                    kwargs to make validation generic.
      is_entity_self_owned(bool): If True, get self-owned SP is performed,
                    this kwargs is used in validate_operation to make sure
                    self-owned SP is not viewed if SP is not self_owned.
      pc_dashboard(obj): PC Dashboard object, if provided, will be used to
                         perform the list validation through UI.
    Returns:
      (tuple): (True, "") if user has View permission and able to
                  perform get operation only on scoped storage policy.
               (False, ERR_MSG) if user does not have View permission or
                  able/unable to perform get operation on non-scoped/scoped
                  storage policy.
    Raises:
      (NuTestError): If entity_id is not passed in kwargs.
    """
    entity_id = kwargs.get("entity_id")
    if not entity_id:
      raise NuTestError("Entity ID is mandatory for get operation.")
    sp_name = self.all_storage_policies[entity_id]
    STEP(f"Verifying SP-get operation for {user} on SP:{sp_name}")

    if kwargs.get("pc_dashboard"):
      # If pc_dashboard is passed, we will be using UI to verify the get operation.
      pc_dashboard = kwargs.get("pc_dashboard")
      sp = pc_dashboard.storage.storage_policies
      sp = sp.view_storage_policy(sp_name)

      INFO(f"Successfully verified READ with {user} for scoped SP:{sp_name}.")
      return True, ""

    sdk_sp = StoragePolicy(self.pc_cluster, interface_type="SDK", username=user,
                           password=password, use_cache=False, debug=True,
                           api_key=self.grbac_helper.user_api_key_mapping.get(user))

    sdk_sp.ext_id = entity_id
    sdk_sp.get(api_key=self.grbac_helper.user_api_key_mapping.get(user),
               **kwargs)
    INFO(f"Successfully verified READ with {user} for scoped SP:{entity_id}.")
    return True, ""

  @validate_operation(["Create_Storage_Policy"])
  def verify_sp_create(self, user, password, **kwargs):
    """
    Method performs storage policies create operation, and verifies it.
    Args:
      user(str): User with which Create op to be performed and verified.
      password(str): Password.
    Kwargs:
      category_id(str): When passed a category ext_id SP is created with
                        category. Default: None
    Returns:
      (tuple): (True, "") If user has SP_Create permission and able to
                  perform create operation only on scoped storage policy. Or
                  vice-versa.
               (False, ERR_MSG) if user does not have Create_SP permission
                  and able to create SP and vice versa.
    """
    category_id = kwargs.get("category_id")
    STEP(f"Verifying SP-Create Op {'with' if category_id else 'without'} "
         f"category for {user}")
    api_kwargs = self.__get_random_sp_spec(user)
    if category_id:
      api_kwargs["category_ext_ids"] = [category_id]
    StoragePolicy.create(
      cluster=self.pc_cluster, interface_type="SDK", username=user,
      password=password, use_cache=False,
      api_key=self.grbac_helper.user_api_key_mapping.get(user),
      **api_kwargs)
    INFO(f"Successfully verified CREATE "
         f"{'with' if category_id else 'without'} for {user}.")
    return True, ""

  @validate_operation(["Update_Storage_Policy"])
  def verify_sp_update(self, user, password, name, **kwargs):
    """
    Method performs storage policies update operation, and verifies it.
    Args:
      user(str): User with which Update op to be performed and verified.
      password(str): Password.
      name(str): SP name to be updated.
    Kwargs:
      entity_id(str): Entity ID.
              Note: Having entity_id in kwargs is mandatory, we are having it in
                    kwargs to make validation generic.
      category_id(str): When passed a category ext_id SP is updated with
                        category. Default: None
      is_entity_self_owned(bool): If True, update self-owned SP is performed,
                    this kwargs is used in validate_operation to make sure
                    self-owned SP is not updated if SP is not self_owned.
    Returns:
      (tuple): (True, "") if user has SP_Update permission and able to
                  perform update operation only on scoped storage policy.
               (False, ERR_MSG) if user does not have Update permission or
                  able/unable to perform update operation on non-scoped/scoped
                  storage policy.
    """
    category_id = kwargs.get("category_id")
    entity_id = kwargs.get("entity_id")

    etag = self.get_etag(entity_id)
    STEP(f"Verifying SP-Update Op {'with' if category_id else 'without'} "
         f"category for {user} on SP:{entity_id}")
    sdk_sp = StoragePolicy(
      self.pc_cluster, interface_type="SDK", username=user,
      password=password, use_cache=False, debug=True,
      api_key=self.grbac_helper.user_api_key_mapping.get(user))
    sdk_sp.ext_id = entity_id
    api_kwargs = self.__get_random_sp_spec(user, name)
    if category_id:
      api_kwargs["category_ext_ids"] = [category_id]

    sdk_sp.edit(etag=etag,
                api_key=self.grbac_helper.user_api_key_mapping.get(user),
                **api_kwargs)
    INFO(f"Successfully verified UPDATE "
         f"{'with' if category_id else 'without'} for {user}.")
    return True, ""

  @validate_operation(["Delete_Storage_Policy"])
  def verify_sp_delete(self, user, password, **kwargs):
    """
    Method performs storage policies delete operation, and verifies it.
    Args:
      user(str): User with which Delete op to be performed and verified.
      password(str): Password.
    Kwargs:
      entity_id(str): Entity ID.
              Note: Having entity_id in kwargs is mandatory, we are having it in
                    kwargs to make validation generic.
      is_entity_self_owned(bool): If True, delete self-owned SP is performed,
                    this kwargs is used in validate_operation to make sure
                    self-owned SP is not deleted if SP is not self_owned.
    Returns:
      (tuple): (True, "") if user has SP_Delete permission and able to
                  perform delete operation only on scoped storage policy.
               (False, ERR_MSG) if user does not have View permission or
                  able/unable to perform get operation on non-scoped/scoped
                  storage policy.
    """
    entity_id = kwargs.get("entity_id")
    etag = self.get_etag(entity_id)
    STEP(f"Verifying SP-Delete operation for {user} on SP:{entity_id}")
    sdk_sp = StoragePolicy(
      self.pc_cluster, interface_type="SDK", username=user,
      password=password, use_cache=False, debug=True,
      api_key=self.grbac_helper.user_api_key_mapping.get(user))
    sdk_sp.ext_id = entity_id
    sdk_sp.remove(validate=True, etag=etag,
                  api_key=self.grbac_helper.user_api_key_mapping.get(user))
    INFO(f"Successfully verified DELETE with {user} for {entity_id}.")
    return True, ""

  def verify_sp_self_owned(self, user, password):
    """
    Method to verify self-owned user for SP.
    Args:
      user(str): Username.
      password(str): Password.
    Returns:
      (tuple): (True, "") When self_owned user functionality is verified
                          successfully.
               (False, ERR_MSG) When self_owned user functionality is not
                          verified successfully.
    """
    STEP(f"Verifying Self owned SP for {user}")
    user_permissions = self.grbac_helper.get_user_permissions(user)

    if not "Create_Storage_Policy" in user_permissions:
      INFO(f"User {user} does not have permission to create SP, "
           f"hence skipping self-owned SP verification.")
      return True, ""
    if not self._is_creation_allowed(user):
      return True, ""
    err_list = []
    api_kwargs = self.__get_random_sp_spec(user)
    self_owned = self.grbac_helper.has_self_owned_acp(user)
    try:
      sp = StoragePolicy.create(
        cluster=self.pc_cluster, interface_type="SDK", username=user,
        password=password, update_model=False, use_cache=False,
        api_key=self.grbac_helper.user_api_key_mapping.get(user), **api_kwargs)

      sp_name = [sp_name for sp_ext_id, sp_name in
                 self.all_storage_policies.items() if sp_ext_id == sp.ext_id][0]
      # Updating the entity_uuid_name_map with the created SP.
      self.grbac_helper.update_entity_uuid_name_map(sp.ext_id, sp_name)

      DEBUG(f"{user} created {sp_name}({sp.ext_id}) to verify self_owned"
            f":{self_owned}")
    except (NuTestPrismError, NuTestError):
      err = f"Policy creation failed for {user} to verify self_owned."
      ERROR(err)
      return False, f"{err} with Traceback: {traceback.format_exc()}."

    all_accessible_entities = self.get_all_user_accessible_entities(user, True)
    inaccessible_entities = \
      list(set(self.all_storage_policies).difference(all_accessible_entities))
    # Since we filter out the user created entities through test in the
    # get_all_user_accessible_entities method, we would be getting
    # the entity in inaccessible as per, hence, we remove it.
    if sp.ext_id in inaccessible_entities:
      DEBUG("Removing the entity from inaccessible entities.")
      inaccessible_entities.remove(sp.ext_id)
    username_containing_sps = [
      cur_sp for cur_sp, sp_name in self.all_storage_policies.items()
      if user.split("@")[0] in sp_name]
    if username_containing_sps:
      DEBUG(f"Removing the entities containing username:{user} from "
            f"inaccessible entities.")
      inaccessible_entities = list(set(inaccessible_entities) -
                                   set(username_containing_sps))
    if inaccessible_entities:
      inaccessible_entity = inaccessible_entities[-1]

    if "View_Storage_Policy" in user_permissions:
      # Verification for self owned View.
      result, err = self.verify_sp_get(user, password, entity_id=sp.entity_id,
                                       is_entity_self_owned=True)
      if not result:
        err_list.append(f"self owned View failed for {user} with err:{err}")
      INFO(f"Verified self-owned View for {user} on {sp_name}")

      if inaccessible_entities:
        # Verification for not self owned View.
        result, err = self.verify_sp_get(user, password,
                                         entity_id=inaccessible_entity,
                                         is_entity_self_owned=False)
        if not result:
          err_list.append(f"Non self owned entity View failed for {user} with "
                          f"err: {err}")
        INFO(f"Verified non self-owned entity View for {user} on "
             f"{inaccessible_entities[-1]}")

    if "Update_Storage_Policy" in user_permissions:
      # Verification for self owned entity Update.
      result, err = self.verify_sp_update(user, password, sp_name,
                                          entity_id=sp.entity_id,
                                          is_entity_self_owned=True)
      if not result:
        err_list.append(f"self owned Update failed for {user} with err:{err}")
      INFO(f"Verified self-owned Update for {user} on {sp_name}")

      # Verification for not self owned entity Update.
      if inaccessible_entities:
        result, err = self.verify_sp_update(
          user, password, sp_name, entity_id=inaccessible_entity,
          is_entity_self_owned=False)
        if not result:
          err_list.append(f"Non self owned entity Update failed for {user} "
                          f"with err:{err}")
        INFO(f"Verified non self-owned entity Update for {user} on "
             f"{inaccessible_entities[-1]}")

    if "Delete_Storage_Policy" in user_permissions:
      result, err = self.verify_sp_delete(user, password,
                                          entity_id=sp.entity_id,
                                          is_entity_self_owned=True)
      if not result:
        err_list.append(f"self owned Delete failed for {user} with err:{err}")
      INFO(f"Verified self-owned Delete for {user} on {sp_name}")

      if inaccessible_entities:
        result, err = self.verify_sp_delete(
          user, password, entity_id=inaccessible_entity,
          is_entity_self_owned=False)
        if not result:
          err_list.append(f"Non self owned entity Delete failed for {user} "
                          f"with err:{err}")
        INFO(f"Verified non self-owned entity Delete for {user} on "
             f"{inaccessible_entities[-1]}")

    if err_list:
      err_msg = "\n".join(err_list)
      ERROR(f"self_owned for {user} failed with error msg:\n{err_msg}")
      return False, err_msg
    return True, ""

  def get_all_user_accessible_entities(self, user, merge_all=False):
    """
    This method returns the list of entities accessible to user.
    Args:
      user(str): username.
      merge_all(bool): If True, different entity type entities are merged
                       into single list, otherwise categorised dict is
                       returned: Default: False
    Returns:
      (dict): If merge_all=False, Dictionary of entities accessible by the user.
      (list): If merge_all=True, List of all entities accessible by the user.
    """
    all_accessible_entities = {}
    for entity in ["vm", "category", "storage_policy"]:
      accessible_entities = self.grbac_helper.\
        user_accessible_entities(user, entity_type=entity)
      if entity == "storage_policy":
        # Since we are performing update/delete ops in the test, refreshed
        # scoped entities are required. Hence, we are adding the SPs which are
        # associated with the categories, to the scoped
        # Figuring out the categories associated with the SPs.
        sp_cats = [cat.ext_id
                   for cat in Categories(cluster=self.pc_cluster).list()
                   if cat.ext_id in accessible_entities]
        sps = StoragePolicy.list(self.pc_cluster, interface_type="SDK")
        cat_assoc_sps = [
          sp.ext_id for sp in sps if set(sp.model.category_ext_ids
                                         if sp.model.category_ext_ids else []
                                         ).intersection(sp_cats)]
        DEBUG(f"Category associated SPs: {cat_assoc_sps}")
        accessible_entities.extend(cat_assoc_sps)
        # We are getting category ext_ids too in accessible entities,
        # removing them.
        accessible_entities = list(set(accessible_entities) - set(sp_cats))
        accessible_entities = [entity for entity in accessible_entities
                               if "/" not in entity]

      if accessible_entities == ["ALL"] and entity == "storage_policy":
        accessible_entities = \
          StoragePolicy.list(self.pc_cluster, interface_type="SDK",
                             use_cache=False)
        accessible_entities = [cur_entity.entity_id for cur_entity in
                               accessible_entities]
      DEBUG(f"User accessible entities for entity type {entity} : "
            f"{accessible_entities}")
      all_accessible_entities[entity] = accessible_entities
    if merge_all:
      all_accessible_entities = functools.reduce(
        lambda lst1, lst2: lst1 + lst2, list(all_accessible_entities.values()))

    return all_accessible_entities

  def associate_categories_to_sps(self):
    """
    Method to associate categories to storage policies.
    Raises:
      (NuTestError): If categories are not enough to associate with SPs.
    """
    all_sps = {sp_id: sp_name for sp_id, sp_name in
               self.all_storage_policies.items() if
               sp_name != 'Default-Storage'}
    all_categories = self.grbac_helper._categories
    sdk_sp = StoragePolicy(self.pc_cluster, interface_type="SDK",
                           use_cache=False)

    all_cats = {f"{cat.key}/{cat.value}": cat.ext_id
                for cat in Categories(cluster=self.pc_cluster).list()
                if f"{cat.key}/{cat.value}" in all_categories}
    all_cats_fqns = list(all_cats.keys())
    associated_sp_cat = {}
    for sp_id, sp_name in all_sps.items():
      current_fqn = all_cats_fqns.pop(0) if all_cats_fqns else None
      if current_fqn:
        sdk_sp.ext_id = sp_id
        api_kwargs = self.__get_random_sp_spec(sp_name=sp_name)
        api_kwargs["category_ext_ids"] = [all_cats[current_fqn]]
        sdk_sp.edit(**api_kwargs)
        associated_sp_cat[current_fqn] = sp_name
      else:
        break
    else:
      raise NuTestError("Categories are not enough to associate with SPs.")
    DEBUG(f"Associated SPs with categories: {associated_sp_cat}")

  def generate_category(self):
    """
    Method to create a category.
    Returns:
      (str): Category ext_id.
    """
    cat = Categories(cluster=self.pc_cluster).create(
      key=f"SP_CatK_{time.time()}",
      value=f"SP_CatV_{time.time()}")
    return cat.data.ext_id

  def get_etag(self, sp_ext_id):
    """
    This method returns the etag of the entity.
    Args:
      sp_ext_id(str): Entity ID.
    Returns:
      (str): Etag of the entity.
    """
    # Fetching the etag of the entity from admin since we might not be able to
    # fetch the etag from the entity for a user not having View permission.
    sdk_sp = StoragePolicy(self.pc_cluster, interface_type="SDK")
    sdk_sp.ext_id = sp_ext_id
    return sdk_sp.get()["data"]["_reserved"]["ETag"]

  @staticmethod
  def _is_operation_authorised(user, exp_status_codes):
    """
    Verifies that user is able to perform the operation only in the case user
    has scope to the entity and permission to perform the operation.
    Args:
      user(str): Username.
      exp_status_codes(list): List of expected status codes.
    Returns:
      (tuple)(bool, str): Tuple of operation authorisation and error msg if any.
    """
    if 200 not in exp_status_codes:
      err = f"{user} without permission, is able to access the policy."
      ERROR(err)
      return False, err
    INFO(f"User {user} successfully fetched SP get data for scoped SP.")
    return True, ""

  @staticmethod
  def _is_operation_unauthorised(user, exp_status_codes):
    """
    Verifies that user is unable to perform the operation only in the case user
    is not assigned to any role, does not have scope to the entity, or lacks
    permission to perform the operation.
    Args:
      user(str): Username.
      exp_status_codes(list): List of expected status codes.
    Returns:
      (tuple)(bool, str): Tuple of operation authorisation and error msg if any.
    """
    if {422, 403}.intersection(set(exp_status_codes)):
      INFO(f"Successfully verified that user {user} is unable to perform "
           f"operation on SP without permission.")
      return True, ""
    err = f"{user}, even with permission, is unable to perform operation on SP."
    ERROR(err)
    return False, err

  def _is_creation_allowed(self, user):
    """
    This method checks if the user has permission to create SP.
    Args:
      user(str): Username.
    Returns:
      (bool): True if user has permission to create SP, False otherwise.
    """
    user_self_owned_status = self.grbac_helper.has_self_owned_acp(user)
    has_scope_sp_all = ("ALL" in
                        self.grbac_helper.user_accessible_entities(
                          user, "storage_policy"))
    if not (has_scope_sp_all or user_self_owned_status):
      DEBUG(f"User does not have permission to create SP, "
            f"has_scope_all:{has_scope_sp_all}, "
            f"user_self_owned_status:{user_self_owned_status}.")
      return False
    return True

  @staticmethod
  def __get_random_sp_spec(user=None, sp_name=None):
    """
    This method returns random storage policy spec.
    Args:
      user(str): Username.
      sp_name(str): Storage policy name.
    Returns:
      (dict): Random storage policy spec.
    """
    # Not keeping encryption as once it is enabled, it can not be disabled.
    api_kwargs = {
      "name": sp_name or "SP_{}_{}".format(user.split('@')[0] if user else "",
                                           time.time()),
      "compression_spec": {
        "compression_state": random.choice(
          ["INLINE", "POSTPROCESS"])
      },
      "fault_tolerance_spec": {
        "replication_factor": random.choice(['TWO', 'THREE'])
      },
      "qos_spec": {
        "throttled_iops": random.randint(100, 2000)
      }
    }
    return api_kwargs