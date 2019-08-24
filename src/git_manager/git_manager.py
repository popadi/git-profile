from sys import exit
from re import search
from os.path import expanduser, isfile
from subprocess import run, PIPE, TimeoutExpired, CalledProcessError

import src.utils.messages as msg
from src.profile.profile import Profile


class GitManager:
    cfg_global_cmd = ["git", "config", "--global"]
    cfg_local_cmd = ["git", "config"]

    def __init__(self, config_file_path=None, quiet=True):
        self.config_file_path = config_file_path
        self.config_file_valid = False
        self.quiet = quiet

    def has_valid_config(self):
        """
        Check if the given config file path is a valid file. If
        no config is provided, a .gitconfig file in the home dir
        will be searched.
        :return: boolean representing the validation answer.
        """
        config_path = (
            self.config_file_path
            if self.config_file_path
            else "{0}/.gitconfig".format(expanduser("~"))
        )

        self.config_file_valid = isfile(config_path)
        if not self.config_file_valid and not self.quiet:
            print(msg.ERR_NO_GITCONFIG)

        self.config_file_path = config_path
        return self.config_file_valid

    def run_command(self, cmd):
        """
        Run the given shell command. If an error or a timeout occurs,
        the program will exit with an appropriate exit code.
        :param cmd: command to be run as an array
        """
        try:
            result = run(cmd, stdout=PIPE)
            return result.stdout.decode("utf-8")
        except TimeoutExpired:
            if not self.quiet:
                print(msg.ERR_RUN_TIMEOUT)
            exit(-1)
        except CalledProcessError as e:
            if not self.quiet:
                print(msg.ERR_RUN_FAILED)
            exit(e.returncode)

    def check_profile_exist(self, profile_name):
        """
        Check if the given profile exists in the config file.
        :return: boolean representing the checking answer.
        """
        command_args = ["git", "config", "--list"]
        properties = self.run_command(command_args)

        if not properties:
            return False

        identifier = "profile.{0}".format(profile_name)
        return identifier in properties

    def get_profile(self, profile_name="user"):
        """
        Given the name of a profile, return an instance of a Profile
        with all its details (username, email, signing key).
        :param profile_name:
        :return:
        """
        default = GitManager.cfg_global_cmd
        user = self.run_command([*default, profile_name + ".name"])
        mail = self.run_command([*default, profile_name + ".email"])
        skey = self.run_command([*default, profile_name + ".signingkey"])

        profile = Profile(user, mail, skey, profile_name)
        return profile

    def set_profile(self, profile, globally=False):
        """
        Set the given profile as being active either locally or globally.
        :param profile: profile to be used to set the required fields
        :param globally: boolean representing the setting mode
        """
        # Get the right prefix for the command
        cmd_prefix = self.cfg_global_cmd if globally else self.cfg_local_cmd

        # Run the commands to set the new active profile
        self.run_command([*cmd_prefix, "user.name", profile.user])
        self.run_command([*cmd_prefix, "user.email", profile.mail])
        if profile.skey:
            self.run_command([*cmd_prefix, "user.signingkey", profile.skey])

        # Update the current-profile entry in the config file
        self.run_command([*cmd_prefix, "current-profile.name", profile.profile_name])

    def add_profile(self, profile):
        """
        Run the necessary commands to add a new profile.
        :param profile: profile details to be added.
        """
        # Set up placeholder and profile title/name
        pn = profile.profile_name
        ph = "profile.{0}.{1}"

        self.run_command([*self.cfg_global_cmd, ph.format(pn, "name"), profile.user])
        self.run_command([*self.cfg_global_cmd, ph.format(pn, "email"), profile.mail])
        if profile.skey:
            self.run_command([*self.cfg_global_cmd, ph.format(pn, "signingkey"), profile.skey])

    def del_profile(self, profile_name):
        """
        Deletes a section from the configuration file. In this case, the
        method deletes the section associated with a previously created
        profile, using this package.
        :param profile_name: the name of the profile to be deleted.
        """
        command = [*self.cfg_global_cmd, "--remove-section", profile_name]
        self.run_command(command)

    def list_profiles(self):
        """
        Return the name of all the profiles created using this package.
        :return: list containing the name of previously created profiles.
        """
        pattern = r"\[profile \"(.*?)\"\]"
        available_profiles = []

        with open(self.config_file_path) as gitconfig:
            for line in gitconfig.readlines():
                match = search(pattern, line)
                if match:
                    available_profiles.append(match.group(1))

        return available_profiles

    def get_current(self, globally=False):
        """
        Get the current set profile by this package.
        :param globally: boolean representing the get mode
        :return: name of the current profile or empty string
        """
        cmd_prefix = self.cfg_global_cmd if globally else self.cfg_local_cmd
        command = [*cmd_prefix, "current-profile.name"]
        return self.run_command(command).strip()
