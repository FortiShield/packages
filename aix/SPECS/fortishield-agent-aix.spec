# Spec file for AIX systems
Name:        fortishield-agent
Version:     5.0.0
Release:     1
License:     GPL
URL:         https://www.fortishield.github.io/
Vendor:      Fortishield, Inc <info@fortishield.github.io>
Packager:    Fortishield, Inc <info@fortishield.github.io>
Summary:     The Fortishield agent, used for threat detection, incident response and integrity monitoring.

Group: System Environment/Daemons
AutoReqProv: no
Source0: %{name}-%{version}.tar.gz
Conflicts: ossec-hids ossec-hids-agent fortishield-manager fortishield-local
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: coreutils automake autoconf libtool

%description
Fortishield is an open source security monitoring solution for threat detection, integrity monitoring, incident response and compliance.

%prep
%setup -q
deps_version=`cat src/Makefile | grep "DEPS_VERSION =" | cut -d " " -f 3`
cd src && gmake clean && gmake deps RESOURCES_URL=http://fortishield.github.io/packages/deps/${deps_version} TARGET=agent
gmake TARGET=agent USE_SELINUX=no
cd ..

%install
# Clean BUILDROOT
rm -fr %{buildroot}

echo 'USER_LANGUAGE="en"' > ./etc/preloaded-vars.conf
echo 'USER_NO_STOP="y"' >> ./etc/preloaded-vars.conf
echo 'USER_INSTALL_TYPE="agent"' >> ./etc/preloaded-vars.conf
echo 'USER_DIR="%{_localstatedir}"' >> ./etc/preloaded-vars.conf
echo 'USER_DELETE_DIR="y"' >> ./etc/preloaded-vars.conf
echo 'USER_ENABLE_ACTIVE_RESPONSE="y"' >> ./etc/preloaded-vars.conf
echo 'USER_ENABLE_SYSCHECK="y"' >> ./etc/preloaded-vars.conf
echo 'USER_ENABLE_ROOTCHECK="y"' >> ./etc/preloaded-vars.conf
echo 'USER_ENABLE_OPENSCAP="n"' >> ./etc/preloaded-vars.conf
echo 'USER_ENABLE_CISCAT="n"' >> ./etc/preloaded-vars.conf
echo 'USER_UPDATE="n"' >> ./etc/preloaded-vars.conf
echo 'USER_AGENT_SERVER_IP="MANAGER_IP"' >> ./etc/preloaded-vars.conf
echo 'USER_CA_STORE="/path/to/my_cert.pem"' >> ./etc/preloaded-vars.conf
echo 'USER_AUTO_START="n"' >> ./etc/preloaded-vars.conf
./install.sh

# Remove unnecessary files or directories
rm -rf %{_localstatedir}/selinux

# Create directories
mkdir -p ${RPM_BUILD_ROOT}%{_init_scripts}
mkdir -p ${RPM_BUILD_ROOT}%{_localstatedir}/.ssh

# Copy the files into RPM_BUILD_ROOT directory
sed "s:FORTISHIELD_HOME_TMP:%{_localstatedir}:g" src/init/templates/ossec-hids-aix.init > src/init/templates/ossec-hids-aix.init.tmp
mv src/init/templates/ossec-hids-aix.init.tmp src/init/templates/ossec-hids-aix.init
/opt/freeware/bin/install -m 0750 src/init/templates/ossec-hids-aix.init ${RPM_BUILD_ROOT}%{_init_scripts}/fortishield-agent
cp -pr %{_localstatedir}/* ${RPM_BUILD_ROOT}%{_localstatedir}/

# Add configuration scripts
mkdir -p ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/
cp gen_ossec.sh ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/
cp add_localfiles.sh ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/

# Support files for dynamic creation of configuraiton file
mkdir -p ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/etc/templates/config/generic
cp -pr etc/templates/config/generic/* ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/etc/templates/config/generic
mkdir -p ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/etc/templates/config/generic/localfile-logs
cp -pr etc/templates/config/generic/localfile-logs/* ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/etc/templates/config/generic/localfile-logs

# Support scripts for post installation
mkdir -p ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/src/init
cp src/init/*.sh ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/src/init

# Add installation scripts
cp src/VERSION ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/src/
cp src/REVISION ${RPM_BUILD_ROOT}%{_localstatedir}/tmp/src/

exit 0

%pre

# Create fortishield user and group
if ! grep "^fortishield:" /etc/group > /dev/null 2>&1; then
  /usr/bin/mkgroup fortishield
fi
if ! grep "^fortishield" /etc/passwd > /dev/null 2>&1; then
  /usr/sbin/useradd fortishield
  /usr/sbin/usermod -G fortishield fortishield
fi

# Remove existent config file and notify user for new installations
if [ $1 = 1 ]; then
  if [ -f %{_localstatedir}/etc/ossec.conf ]; then
    echo "A backup from your ossec.conf has been created at %{_localstatedir}/etc/ossec.conf.rpmorig"
    echo "Please verify your ossec.conf configuration at %{_localstatedir}/etc/ossec.conf"
    mv %{_localstatedir}/etc/ossec.conf %{_localstatedir}/etc/ossec.conf.rpmorig
  fi
fi

if [ $1 = 2 ]; then
  if /etc/rc.d/init.d/fortishield-agent status 2>/dev/null | grep "is running" > /dev/null 2>&1; then
    /etc/rc.d/init.d/fortishield-agent stop > /dev/null 2>&1 || :
    touch %{_localstatedir}/tmp/fortishield.restart
  fi
  %{_localstatedir}/bin/ossec-control stop > /dev/null 2>&1 || %{_localstatedir}/bin/fortishield-control stop > /dev/null 2>&1
fi

if [ $1 = 2 ]; then
  if [ -d %{_localstatedir}/logs/ossec ]; then
    cp -rp %{_localstatedir}/logs/ossec %{_localstatedir}/tmp/logs/fortishield > /dev/null 2>&1
    rm -rf %{_localstatedir}/logs/ossec/*
    rm -rf %{_localstatedir}/logs/ossec/.??*
  fi

  if [ -d %{_localstatedir}/queue/ossec ]; then
    cp -rp %{_localstatedir}/queue/ossec %{_localstatedir}/tmp/queue/sockets > /dev/null 2>&1
    rm -rf %{_localstatedir}/queue/ossec/*
    rm -rf %{_localstatedir}/queue/ossec/.??*
  fi
fi

%post

if [ $1 = 2 ]; then
  if [ -d %{_localstatedir}/tmp/logs/fortishield ]; then
    rm -rf %{_localstatedir}/logs/fortishield
    mv %{_localstatedir}/tmp/logs/ossec %{_localstatedir}/logs/fortishield> /dev/null 2>&1
  fi

  if [ -d %{_localstatedir}/tmp/queue/sockets ]; then
    rm -rf %{_localstatedir}/queue/sockets
    mv %{_localstatedir}/tmp/queue/ossec %{_localstatedir}/queue/sockets > /dev/null 2>&1
  fi
fi

# New installations
if [ $1 = 1 ]; then

  # Generating ossec.conf file
  . %{_localstatedir}/tmp/src/init/dist-detect.sh
  %{_localstatedir}/tmp/gen_ossec.sh conf agent ${DIST_NAME} ${DIST_VER}.${DIST_SUBVER} %{_localstatedir} > %{_localstatedir}/etc/ossec.conf

  # Add default local_files to ossec.conf
  %{_localstatedir}/tmp/add_localfiles.sh %{_localstatedir} >> %{_localstatedir}/etc/ossec.conf

  # Restore Fortishield agent configuration
  if [ -f %{_localstatedir}/etc/ossec.conf.rpmorig ]; then
    %{_localstatedir}/tmp/src/init/replace_manager_ip.sh %{_localstatedir}/etc/ossec.conf.rpmorig %{_localstatedir}/etc/ossec.conf
  fi

  # Fix for AIX: netstat command
  sed 's/netstat -tulpn/netstat -tu/' %{_localstatedir}/etc/ossec.conf > %{_localstatedir}/etc/ossec.conf.tmp
  mv %{_localstatedir}/etc/ossec.conf.tmp %{_localstatedir}/etc/ossec.conf
  sed 's/sort -k 4 -g/sort -n -k 4/' %{_localstatedir}/etc/ossec.conf > %{_localstatedir}/etc/ossec.conf.tmp
  mv %{_localstatedir}/etc/ossec.conf.tmp %{_localstatedir}/etc/ossec.conf

  # Generate the active-responses.log file
  touch %{_localstatedir}/logs/active-responses.log
  chown fortishield:fortishield %{_localstatedir}/logs/active-responses.log
  chmod 0660 %{_localstatedir}/logs/active-responses.log

  %{_localstatedir}/tmp/src/init/register_configure_agent.sh %{_localstatedir} > /dev/null || :

fi
chown root:fortishield %{_localstatedir}/etc/ossec.conf
ln -fs /etc/rc.d/init.d/fortishield-agent /etc/rc.d/rc2.d/S97fortishield-agent
ln -fs /etc/rc.d/init.d/fortishield-agent /etc/rc.d/rc3.d/S97fortishield-agent

rm -rf %{_localstatedir}/tmp/etc
rm -rf %{_localstatedir}/tmp/src
rm -f %{_localstatedir}/tmp/add_localfiles.sh

chmod 0660 %{_localstatedir}/etc/ossec.conf

# Remove old ossec user and group if exists and change ownwership of files

if grep "^ossec:" /etc/group > /dev/null 2>&1; then
  find %{_localstatedir}/ -group ossec -user root -exec chown root:fortishield {} \; > /dev/null 2>&1 || true
  if grep "^ossec" /etc/passwd > /dev/null 2>&1; then
    find %{_localstatedir}/ -group ossec -user ossec -exec chown fortishield:fortishield {} \; > /dev/null 2>&1 || true
    userdel ossec
  fi
  if grep "^ossecm" /etc/passwd > /dev/null 2>&1; then
    find %{_localstatedir}/ -group ossec -user ossecm -exec chown fortishield:fortishield {} \; > /dev/null 2>&1 || true
    userdel ossecm
  fi
  if grep "^ossecr" /etc/passwd > /dev/null 2>&1; then
    find %{_localstatedir}/ -group ossec -user ossecr -exec chown fortishield:fortishield {} \; > /dev/null 2>&1 || true
    userdel ossecr
  fi
  rmgroup ossec
fi

if [ -f %{_localstatedir}/tmp/fortishield.restart ]; then
  rm -f %{_localstatedir}/tmp/fortishield.restart
  /etc/rc.d/init.d/fortishield-agent restart > /dev/null 2>&1 || :
fi

%preun

if [ $1 = 0 ]; then

  /etc/rc.d/init.d/fortishield-agent stop > /dev/null 2>&1 || :
  rm -f %{_localstatedir}/queue/sockets/*
  rm -f %{_localstatedir}/queue/sockets/.agent_info || :
  rm -f %{_localstatedir}/queue/sockets/.wait || :
  rm -f %{_localstatedir}/queue/diff/*
  rm -f %{_localstatedir}/queue/alerts/*
  rm -f %{_localstatedir}/queue/rids/*

fi


%postun

# Remove fortishield user and group
if [ $1 = 0 ];then
  if grep "^fortishield" /etc/passwd > /dev/null 2>&1; then
    userdel fortishield
  fi
  if grep "^fortishield:" /etc/group > /dev/null 2>&1; then
    rmgroup fortishield
  fi

  rm -rf %{_localstatedir}/ruleset
fi

%clean
rm -fr %{buildroot}

%files
%{_init_scripts}/*

%dir %attr(750, root, fortishield) %{_localstatedir}
%attr(750, root, fortishield) %{_localstatedir}/agentless
%dir %attr(770, root, fortishield) %{_localstatedir}/.ssh
%dir %attr(750, root, fortishield) %{_localstatedir}/active-response
%dir %attr(750, root, fortishield) %{_localstatedir}/active-response/bin
%attr(750, root, fortishield) %{_localstatedir}/active-response/bin/*
%dir %attr(750, root,system) %{_localstatedir}/bin
%attr(750, root,system) %{_localstatedir}/bin/*
%dir %attr(750, root, fortishield) %{_localstatedir}/backup
%dir %attr(770, fortishield, fortishield) %{_localstatedir}/etc
%attr(640, root, fortishield) %config(noreplace) %{_localstatedir}/etc/client.keys
%attr(640, root, fortishield) %{_localstatedir}/etc/internal_options*
%attr(640, root, fortishield) %config(noreplace) %{_localstatedir}/etc/local_internal_options.conf
%attr(660, root, fortishield) %config(noreplace) %{_localstatedir}/etc/ossec.conf
%attr(640, root, fortishield) %{_localstatedir}/etc/wpk_root.pem
%dir %attr(770, root, fortishield) %{_localstatedir}/etc/shared
%attr(660, root, fortishield) %config(missingok,noreplace) %{_localstatedir}/etc/shared/*
%dir %attr(750, root, system) %{_localstatedir}/lib
%attr(750, root, fortishield) %{_localstatedir}/lib/*
%dir %attr(770, fortishield, fortishield) %{_localstatedir}/logs
%attr(660, fortishield, fortishield) %ghost %{_localstatedir}/logs/active-responses.log
%attr(660, root, fortishield) %ghost %{_localstatedir}/logs/ossec.log
%attr(660, root, fortishield) %ghost %{_localstatedir}/logs/ossec.json
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/logs/fortishield
%dir %attr(750, root, fortishield) %{_localstatedir}/queue
%dir %attr(770, fortishield, fortishield) %{_localstatedir}/queue/sockets
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/diff
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/fim
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/fim/db
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/syscollector
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/syscollector/db
%attr(640, root, fortishield) %{_localstatedir}/queue/syscollector/norm_config.json
%dir %attr(770, fortishield, fortishield) %{_localstatedir}/queue/alerts
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/rids
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/queue/logcollector
%dir %attr(750, fortishield, fortishield) %{_localstatedir}/ruleset/sca
%attr(640, root, fortishield) %{_localstatedir}/ruleset/sca/*
%dir %attr(1750, root, fortishield) %{_localstatedir}/tmp
%attr(750, root,system) %config(missingok) %{_localstatedir}/tmp/add_localfiles.sh
%attr(750, root,system) %config(missingok) %{_localstatedir}/tmp/gen_ossec.sh
%dir %attr(1750, root, fortishield) %config(missingok) %{_localstatedir}/tmp/etc/templates
%dir %attr(1750, root, fortishield) %config(missingok) %{_localstatedir}/tmp/etc/templates/config
%dir %attr(1750, root, fortishield) %config(missingok) %{_localstatedir}/tmp/etc/templates/config/generic
%attr(750, root,system) %config(missingok) %{_localstatedir}/tmp/etc/templates/config/generic/*.template
%dir %attr(1750, root, fortishield) %config(missingok) /var/ossec/tmp/etc/templates/config/generic/localfile-logs
%attr(750, root,system) %config(missingok) /var/ossec/tmp/etc/templates/config/generic/localfile-logs/*.template
%attr(750, root,system) %config(missingok) %{_localstatedir}/tmp/src/*
%dir %attr(750, root, fortishield) %{_localstatedir}/var
%dir %attr(770, root, fortishield) %{_localstatedir}/var/incoming
%dir %attr(770, root, fortishield) %{_localstatedir}/var/run
%dir %attr(770, root, fortishield) %{_localstatedir}/var/upgrade
%dir %attr(770, root, fortishield) %{_localstatedir}/var/wodles
%dir %attr(750, root, fortishield) %{_localstatedir}/wodles
%attr(750, root, fortishield) %{_localstatedir}/wodles/*

%changelog
* Tue Oct 01 2024 support <info@fortishield.github.io> - 5.0.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-5-0-0.html
* Tue May 14 2024 support <info@fortishield.github.io> - 4.9.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-9-0.html
* Tue Mar 26 2024 support <info@fortishield.github.io> - 4.8.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-8-2.html
* Wed Feb 28 2024 support <info@fortishield.github.io> - 4.8.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-8-1.html
* Wed Feb 21 2024 support <info@fortishield.github.io> - 4.8.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-8-0.html
* Tue Jan 09 2024 support <info@fortishield.github.io> - 4.7.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-7-2.html
* Wed Dec 13 2023 support <info@fortishield.github.io> - 4.7.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-7-1.html
* Tue Nov 21 2023 support <info@fortishield.github.io> - 4.7.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-7-0.html
* Tue Oct 31 2023 support <info@fortishield.github.io> - 4.6.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-6-0.html
* Tue Oct 24 2023 support <info@fortishield.github.io> - 4.5.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-5-4.html
* Tue Oct 10 2023 support <info@fortishield.github.io> - 4.5.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-5-3.html
* Thu Aug 31 2023 support <info@fortishield.github.io> - 4.5.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-5-2.html
* Thu Aug 24 2023 support <info@fortishield.github.io> - 4.5.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-5.1.html
* Thu Aug 10 2023 support <info@fortishield.github.io> - 4.5.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-5-0.html
* Mon Jul 10 2023 support <info@fortishield.github.io> - 4.4.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-5.html
* Tue Jun 13 2023 support <info@fortishield.github.io> - 4.4.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-4.html
* Thu May 25 2023 support <info@fortishield.github.io> - 4.4.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-3.html
* Mon May 08 2023 support <info@fortishield.github.io> - 4.4.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-2.html
* Mon Apr 24 2023 support <info@fortishield.github.io> - 4.3.11
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3.11.html
* Mon Apr 17 2023 support <info@fortishield.github.io> - 4.4.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-1.html
* Wed Jan 18 2023 support <info@fortishield.github.io> - 4.4.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-4-0.html
* Thu Nov 10 2022 support <info@fortishield.github.io> - 4.3.10
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-10.html
* Mon Oct 03 2022 support <info@fortishield.github.io> - 4.3.9
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-9.html
* Wed Sep 21 2022 support <info@fortishield.github.io> - 3.13.6
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-6.html
* Mon Sep 19 2022 support <info@fortishield.github.io> - 4.3.8
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-8.html
* Wed Aug 24 2022 support <info@fortishield.github.io> - 3.13.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-5.html
* Mon Aug 08 2022 support <info@fortishield.github.io> - 4.3.7
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-7.html
* Thu Jul 07 2022 support <info@fortishield.github.io> - 4.3.6
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-6.html
* Wed Jun 29 2022 support <info@fortishield.github.io> - 4.3.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-5.html
* Tue Jun 07 2022 support <info@fortishield.github.io> - 4.3.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-4.html
* Tue May 31 2022 support <info@fortishield.github.io> - 4.3.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-3.html
* Mon May 30 2022 support <info@fortishield.github.io> - 4.3.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-2.html
* Mon May 30 2022 support <info@fortishield.github.io> - 3.13.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-4.html
* Sun May 29 2022 support <info@fortishield.github.io> - 4.2.7
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-7.html
* Wed May 18 2022 support <info@fortishield.github.io> - 4.3.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-1.html
* Thu May 05 2022 support <info@fortishield.github.io> - 4.3.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-3-0.html
* Fri Mar 25 2022 support <info@fortishield.github.io> - 4.2.6
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-6.html
* Mon Nov 15 2021 support <info@fortishield.github.io> - 4.2.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-5.html
* Thu Oct 21 2021 support <info@fortishield.github.io> - 4.2.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-4.html
* Wed Oct 06 2021 support <info@fortishield.github.io> - 4.2.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-3.html
* Tue Sep 28 2021 support <info@fortishield.github.io> - 4.2.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-2.html
* Sat Sep 25 2021 support <info@fortishield.github.io> - 4.2.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-1.html
* Mon Apr 26 2021 support <info@fortishield.github.io> - 4.2.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-2-0.html
* Sat Apr 24 2021 support <info@fortishield.github.io> - 3.13.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-3.html
* Thu Apr 22 2021 support <info@fortishield.github.io> - 4.1.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-5.html
* Mon Mar 29 2021 support <info@fortishield.github.io> - 4.1.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-4.html
* Sat Mar 20 2021 support <info@fortishield.github.io> - 4.1.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-3.html
* Mon Mar 08 2021 support <info@fortishield.github.io> - 4.1.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-2.html
* Fri Mar 05 2021 support <info@fortishield.github.io> - 4.1.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-1.html
* Tue Jan 19 2021 support <info@fortishield.github.io> - 4.1.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-1-0.html
* Mon Nov 30 2020 support <info@fortishield.github.io> - 4.0.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-0-3.html
* Mon Nov 23 2020 support <info@fortishield.github.io> - 4.0.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-0-2.html
* Sat Oct 31 2020 support <info@fortishield.github.io> - 4.0.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-0-1.html
* Mon Oct 19 2020 support <info@fortishield.github.io> - 4.0.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-4-0-0.html
* Fri Aug 21 2020 support <info@fortishield.github.io> - 3.13.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-2.html
* Tue Jul 14 2020 support <info@fortishield.github.io> - 3.13.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-1.html
* Mon Jun 29 2020 support <info@fortishield.github.io> - 3.13.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-13-0.html
* Wed May 13 2020 support <info@fortishield.github.io> - 3.12.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-12-3.html
* Thu Apr 9 2020 support <info@fortishield.github.io> - 3.12.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-12-2.html
* Wed Apr 8 2020 support <info@fortishield.github.io> - 3.12.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-12-1.html
* Wed Mar 25 2020 support <info@fortishield.github.io> - 3.12.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-12-0.html
* Mon Feb 24 2020 support <info@fortishield.github.io> - 3.11.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-11-4.html
* Wed Jan 22 2020 support <info@fortishield.github.io> - 3.11.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-11-3.html
* Tue Jan 7 2020 support <info@fortishield.github.io> - 3.11.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-11-2.html
* Thu Dec 26 2019 support <info@fortishield.github.io> - 3.11.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-11-1.html
* Mon Oct 7 2019 support <info@fortishield.github.io> - 3.11.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-11-0.html
* Mon Sep 23 2019 support <support@fortishield.github.io> - 3.10.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-10-2.html
* Thu Sep 19 2019 support <support@fortishield.github.io> - 3.10.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-10-1.html
* Mon Aug 26 2019 support <support@fortishield.github.io> - 3.10.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-10-0.html
* Thu Aug 8 2019 support <support@fortishield.github.io> - 3.9.5
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-5.html
* Fri Jul 12 2019 support <support@fortishield.github.io> - 3.9.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-4.html
* Tue Jul 02 2019 support <support@fortishield.github.io> - 3.9.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-3.html
* Tue Jun 11 2019 support <support@fortishield.github.io> - 3.9.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-2.html
* Sat Jun 01 2019 support <support@fortishield.github.io> - 3.9.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-1.html
* Mon Feb 25 2019 support <support@fortishield.github.io> - 3.9.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-9-0.html
* Wed Jan 30 2019 support <support@fortishield.github.io> - 3.8.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-8-2.html
* Thu Jan 24 2019 support <support@fortishield.github.io> - 3.8.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-8-1.html
* Fri Jan 18 2019 support <support@fortishield.github.io> - 3.8.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-8-0.html
* Wed Nov 7 2018 support <support@fortishield.github.io> - 3.7.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-7-0.html
* Mon Sep 10 2018 support <info@fortishield.github.io> - 3.6.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-6-1.html
* Fri Sep 7 2018 support <support@fortishield.github.io> - 3.6.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-6-0.html
* Wed Jul 25 2018 support <support@fortishield.github.io> - 3.5.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-5-0.html
* Wed Jul 11 2018 support <support@fortishield.github.io> - 3.4.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-4-0.html
* Mon Jun 18 2018 support <support@fortishield.github.io> - 3.3.1
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-3-1.html
* Mon Jun 11 2018 support <support@fortishield.github.io> - 3.3.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-3-0.html
* Wed May 30 2018 support <support@fortishield.github.io> - 3.2.4
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-2-4.html
* Thu May 10 2018 support <support@fortishield.github.io> - 3.2.3
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-2-3.html
* Mon Apr 09 2018 support <support@fortishield.github.io> - 3.2.2
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-2-2.html
* Wed Feb 21 2018 support <support@fortishield.github.io> - 3.2.1
- More info: https://documentation.fortishield.github.io/current/release-notes/rerlease-3-2-1.html
* Wed Feb 07 2018 support <support@fortishield.github.io> - 3.2.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-2-0.html
* Thu Dec 21 2017 support <support@fortishield.github.io> - 3.1.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-1-0.html
* Mon Nov 06 2017 support <support@fortishield.github.io> - 3.0.0
- More info: https://documentation.fortishield.github.io/current/release-notes/release-3-0-0.html
