"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.
Author: shubham.shrivastava@nutanix.com

This file contains test methods to perform Storage Policy CRUD for SP-GRBAC
FEAT.
"""
#pylint: disable=unused-variable, too-many-locals, too-many-statements
#pylint: disable=too-many-branches

import os
import pprint
import random
from random import sample
from framework.interfaces.consts import PRISM_PASSWORD_WITHOUT_PAM
from framework.lib.nulog import INFO, STEP
from framework.lib.test.nos_test import NOSTest

from workflows.iam.sdk.v4.acp.acp import ACP
from workflows.cdp.stargate.qos.setup_workflow import SetupWorkflow
from workflows.cdp.common.generic import generate_html_report
from workflows.cdp.test_orchestrator.storage_policy_utils.\
  storage_policy_grbac_helper import StoragePolicyGRBACHelper
from workflows.manageability.ui.cdp.ui_workflows.pc.prism_central import \
  PrismCentral
from workflows.workload_orchestrator.lib.ops_tracker import OpsTracker
from workflows.workload_orchestrator.lib.wlo_helpers import (
  populate_testcase_ops)


class TestStoragePolicyRBAC(NOSTest):
  """
  GRBAC test for Storage Policies
  """
  def class_setup(self):
    """ Class setup to instantiate other helper classes """
    self.sw = SetupWorkflow(self)
    self.sw.setup_infra()
    self.sw.prepare_test_setup(self.test_args)
    self.sp_rbac_helper = StoragePolicyGRBACHelper(self, self.test_args)
    self.selenium = self.get_resources_by_type(self.SELENIUM_VM)[0]

  def setup(self):
    """
    Prepare the GRBAC setup.
    """
    STEP("Preparing the setup for SP RBAC")
    config_file = self.test_args.get("user_role_config_file")
    # Checking if we have user_type override for test.
    if self.test_args.get("user_type"):
      self.sp_rbac_helper.grbac_helper.global_user_type = \
        self.test_args.get("user_type")
    else:
      self.sp_rbac_helper.grbac_helper.global_user_type = "RANDOM"
    INFO("Will be creating {} type users.".format(
      self.sp_rbac_helper.grbac_helper.global_user_type))

    self.sp_rbac_helper.grbac_helper.everything_rbac(config_file)
    self.sp_rbac_helper.associate_categories_to_sps()
    self.pc_clusters = self.get_resources_by_type(self.PRISM_CENTRAL)
    self.test_result = []
    self.headers = ("Op ID.", "Operation", "User", "Storage Policy", "Result",
                    "Message")
    self.ops_tracker = OpsTracker()
    for user in (
        self.sp_rbac_helper.grbac_helper.get_users_group(user_type=None)):
      if user in self.sp_rbac_helper.grbac_helper.user_role_mapping:
        for operation in self.test_args.get("test_operations"):
          self.ops_tracker.add_ops_total(1,
                                         caller_name=f"{user.name}_{operation}")

    if self.test_args["ui_test"]:
      # UI setup.
      self.test_args['selenium_server'] = self.selenium.ip
      self.pc_ip = self.pc_clusters[0].svm_ips[0]

  def test_storage_policy_grbac(self):
    """
      Metadata:
        Summary: This test performs storage_policy/list operation on all the
             users with different roles and scoped user.
        Priority: $P0
        Requirements: [FEAT-13109, FEAT-14586, FEAT-16871]
        Components: [$STARGATE]
        Services: [$PC_TAR]
        Tags: [$AHV]
        Steps:
          - For a users, perform storage_policy/list operation
          - ExpectedResults
          - View permission User should be able to view scoped SPs
          - Edit permission User should be able to edit scoped SPs
          - Delete permission User should be able to delete scoped SPs
          - Create permission User should be able to create SPs
          - DSP should not get updated and deleted even with permissions
          - With permission, self owned SP should be operable for the user

    """
    all_user_result = []
    op_id = 0
    # DSP is not allowed to be updated, deleted, or updated. We are testing DSP
    # Ops as separately. Setting dsp_ext_id once here.
    dsp_ext_id = [sp_ext_id for sp_ext_id, sp_name in
                  self.sp_rbac_helper.all_storage_policies.items() if sp_name
                  == "Default-Storage"][0]
    for user in (
        self.sp_rbac_helper.grbac_helper.get_users_group(user_type=None)):
      user = user.name
      # Useful for prefilled setup with groups too with multiple LDAP users.
      if user not in self.sp_rbac_helper.grbac_helper.user_role_mapping:
        INFO("User '{}' not assigned any role. Skipping.".format(user))
        continue

      user_permissions = (
        self.sp_rbac_helper.grbac_helper.get_user_permissions(user))
      user_permissions = "{}:{}".format(user, user_permissions)
      STEP(f"Running tests for user: {user} with {user_permissions}")
      self.pc_dashboard = None
      if self.test_args["ui_test"]:
        self.test_args["pc_user"] = user
        self.test_args["pc_passwd"] = PRISM_PASSWORD_WITHOUT_PAM
        self.pc_dashboard = PrismCentral(self.test_args, pc_ip=self.pc_ip)

      # LIST
      op = "LIST"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, msg = (
          self.sp_rbac_helper.verify_sp_list(user, PRISM_PASSWORD_WITHOUT_PAM,
                                             pc_dashboard=self.pc_dashboard))
        STEP(f"{user} {op} with {user_permissions} TEST"
             f" {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "",
                                 "PASSED" if result else "FAILED", msg))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # LIST ODATA
      op = "LIST_ODATA"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, msg = (
          self.sp_rbac_helper.verify_sp_list(user, PRISM_PASSWORD_WITHOUT_PAM,
                                             self.test_args.get("odata_list")))
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "",
                                 "PASSED" if result else "FAILED", msg))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # READ
      op = "READ"
      if op in self.test_args.get("test_operations"):
        each_sp_results = []
        sps = self.sp_rbac_helper.all_storage_policies
        sps = {ext_id:name for ext_id, name in sps.items()
               if user.split("@")[0] not in name}
        # Performing read operation on 6 random SPs.
        entities = random.sample(list(sps.items()), 6)
        for entity_id, name in entities:
          op_id += 1
          result, msg = \
            self.sp_rbac_helper.verify_sp_get(user, PRISM_PASSWORD_WITHOUT_PAM,
                                              entity_id=entity_id,
                                              pc_dashboard=self.pc_dashboard)
          STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
          self.test_result.append((op_id, op, user_permissions, name,
                                   "PASSED" if result else "FAILED", msg))
          all_user_result.append(result)
          each_sp_results.append(result)
        if all(each_sp_results):
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # CREATE WITHOUT CATEGORY
      op = "CREATE_WITHOUT_CATEGORY"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, err = \
          self.sp_rbac_helper.verify_sp_create(user, PRISM_PASSWORD_WITHOUT_PAM)
        self.test_result.append((op_id, op, user_permissions, "",
                                 "PASSED" if result else "FAILED", err))
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # CREATE WITH CATEGORY
      op = "CREATE_WITH_CATEGORY"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        cat_ext_id = self.sp_rbac_helper.generate_category()
        result, err = \
          self.sp_rbac_helper.verify_sp_create(user, PRISM_PASSWORD_WITHOUT_PAM,
                                               category_id=cat_ext_id)
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "",
                                 "PASSED" if result else "FAILED", err))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # UPDATE
      op = "UPDATE_WITHOUT_CATEGORY"
      each_sp_results = []
      if op in self.test_args.get("test_operations"):
        all_sps = self.sp_rbac_helper.all_storage_policies
        # Taking a sample of 5 entities to update, ensuring that sp
        # is not DSP and not self_owned (username is not in the SP name).
        entity_ids = sample(
          list([sp_ext_id for sp_ext_id, sp_name in all_sps.items()
                if sp_ext_id != dsp_ext_id and
                user.split("@")[0] not in sp_name]), 5)

        # UPDATE without Category
        for entity_id in entity_ids:
          op_id += 1
          sp_name = all_sps[entity_id]
          result, err = \
            self.sp_rbac_helper.verify_sp_update(
              user, PRISM_PASSWORD_WITHOUT_PAM, sp_name, entity_id=entity_id)
          STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
          self.test_result.append((op_id, op, user_permissions, sp_name,
                                   "PASSED" if result else "FAILED", err))
          all_user_result.append(result)
          each_sp_results.append(result)
        if all(each_sp_results):
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # UPDATE with Category
      op = "UPDATE_WITH_CATEGORY"
      each_sp_results_with_cat = []
      if op in self.test_args.get("test_operations"):
        all_sps = self.sp_rbac_helper.all_storage_policies
        entity_ids = sample(
          list([sp_ext_id for sp_ext_id, sp_name in
                all_sps.items() if sp_ext_id != dsp_ext_id
                and user.split("@")[0] not in sp_name]), 5)
        for entity_id in entity_ids:
          op_id += 1
          sp_name = all_sps[entity_id]
          cat_ext_id = self.sp_rbac_helper.generate_category()
          result, err = \
            self.sp_rbac_helper.verify_sp_update(
              user, PRISM_PASSWORD_WITHOUT_PAM, sp_name, entity_id=entity_id,
              category_id=cat_ext_id)
          STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
          self.test_result.append((op_id, op, user_permissions, sp_name,
                                   "PASSED" if result else "FAILED", err))
          all_user_result.append(result)
          each_sp_results_with_cat.append(result)
        if all(each_sp_results_with_cat):
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # UPDATE DSP
      op = "UPDATE_DSP"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, err = self.sp_rbac_helper.verify_sp_update(
          user, PRISM_PASSWORD_WITHOUT_PAM, name="Default-Storage",
          entity_id=dsp_ext_id)
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "Default-Storage",
                                 "PASSED" if result else "FAILED", err))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # DELETE
      op = "DELETE"
      if op in self.test_args.get("test_operations"):
        all_sps = self.sp_rbac_helper.all_storage_policies
        # Taking a sample of 2 entities to delete except DSP.
        entity_ids = sample(
          [sp_ext_id for sp_ext_id, sp_name in all_sps.items()
           if ((not self.test_args.get("delete_sp_prefix") or
                sp_name.startswith(self.test_args.get("delete_sp_prefix")))
               and sp_ext_id != dsp_ext_id
               and user.split("@")[0] not in sp_name)], 2)
        each_sp_results = []
        for entity_id in entity_ids:
          op_id += 1
          result, err = self.sp_rbac_helper.verify_sp_delete(
            user, PRISM_PASSWORD_WITHOUT_PAM, entity_id=entity_id)
          STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
          self.test_result.append((op_id, op, user_permissions,
                                   all_sps[entity_id],
                                   "PASSED" if result else "FAILED", err))
          all_user_result.append(result)
          each_sp_results.append(result)
        if all(each_sp_results):
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # DELETE DSP
      op = "DELETE_DSP"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, err = self.sp_rbac_helper.verify_sp_delete(
          user, PRISM_PASSWORD_WITHOUT_PAM, entity_id=dsp_ext_id)
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "Default-Storage",
                                 "PASSED" if result else "FAILED", err))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

      # SELF_OWNED
      op = "SELF_OWNED"
      if op in self.test_args.get("test_operations"):
        op_id += 1
        result, err = self.sp_rbac_helper.verify_sp_self_owned(
          user, PRISM_PASSWORD_WITHOUT_PAM)
        STEP(f"{user} {op} TEST {'PASSED' if result else 'FAILED'}!!")
        self.test_result.append((op_id, op, user_permissions, "",
                                 "PASSED" if result else "FAILED", err))
        all_user_result.append(result)
        if result:
          self.ops_tracker.add_ops_completed(num=1, caller_name=f"{user}_{op}")

    if not all(all_user_result):
      STEP("PLEASE CHECK '{}' for detailed report".format(
        os.path.join(os.environ['NUTEST_LOGDIR'], 'SP_GRBAC_Failure.html')))
    assert all(all_user_result), "One or more tests failed."

  def teardown(self):
    """
    Clean up the grbac setup.
    """
    # We log the result in HTML in case of failure.
    if self.result["result"] in ("FAILED", "ERROR"):
      test_log_dir = os.environ['NUTEST_LOGDIR']
      # We generate the html report in case of failure.
      html = generate_html_report(
        self.test_result, self.headers,
        title="Storage Policy GRBAC Test Result",
        popup_link_text="Error Message", popup_column_index=5,
        value_cell_color={"PASSED": "#d1ffbd", "FAILED":"#ffcccb"})
      with (open(os.path.join(test_log_dir, 'SP_GRBAC_Failure.html'), "w") as
            file_handle):
        file_handle.write(html)
    populate_testcase_ops(self, self.ops_tracker,
                          self.result["result"] != "PASSED",
                          self.test_args.get("populate_result", False))

    # User-role-permission info.
    for user in (
        self.sp_rbac_helper.grbac_helper.get_users_group(user_type=None)):
      user_name = user.name
      if user_name not in self.sp_rbac_helper.grbac_helper.user_role_mapping:
        INFO(f"User '{user_name}' not assigned any role. Skipping.")
        continue
      user_permissions = self.sp_rbac_helper.grbac_helper.get_user_permissions(
        user_name)
      user_permissions_str = f"{user_name}:{user_permissions}"
      INFO(f"{user_name} permissions: with {user_permissions_str}")
      INFO("{} role: {}".format(
        user_name,
        self.sp_rbac_helper.grbac_helper.user_role_mapping[user_name][0].name))

    # User ACP info.
    acp_sdk = ACP(cluster=self.pc_clusters[0])
    acps = [acp for acp in acp_sdk.list_acp() if
            acp.get("authorization_policy_type") == "USER_DEFINED"]
    INFO(
      "ACP Info: {}".format("\n\n#".join(pprint.pformat(acp) for acp in acps)))

    self.sw.cleanup(testobj=self)
    self.sp_rbac_helper.grbac_helper.cleanup_rbac()