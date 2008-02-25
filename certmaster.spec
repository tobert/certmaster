
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%define is_suse %(test -e /etc/SuSE-release && echo 1 || echo 0)

Summary: Remote certificate distribution framework
Name: certmaster
Source1: version
Version: %(echo `awk '{ print $1 }' %{SOURCE1}`)
Release: %(echo `awk '{ print $2 }' %{SOURCE1}`)%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPLv2+
Group: Applications/System
Requires: python >= 2.3
Requires: pyOpenSSL
BuildRequires: python-devel
%if %is_suse
BuildRequires: gettext-devel
%else
%if 0%{?fedora} >= 8
BuildRequires: python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif
%endif
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: https://fedorahosted.org/certmaster

%description

certmaster is a easy mechanism for distributing SSL certificates

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT

%clean
rm -fr $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
%if 0%{?fedora} > 8
%{python_sitelib}/certmaster*.egg-info
%endif
%{_bindir}/certmaster
%{_bindir}/certmaster-request
%{_bindir}/certmaster-ca
/etc/init.d/certmaster
%dir %{_sysconfdir}/%{name}
%dir %{_sysconfdir}/%{name}/minion-acl.d/
%dir %{_sysconfdir}/pki/%{name}
%config(noreplace) /etc/certmaster/minion.conf
%config(noreplace) /etc/certmaster/certmaster.conf
%config(noreplace) /etc/logrotate.d/certmaster_rotate
%dir %{python_sitelib}/certmaster
%dir %{python_sitelib}/certmaster/minion
%dir %{python_sitelib}/certmaster/overlord
%{python_sitelib}/certmaster/minion/*.py*
%{python_sitelib}/certmaster/overlord/*.py*
%{python_sitelib}/certmaster/*.py*
%dir /var/log/certmaster
%dir /var/lib/certmaster
%doc AUTHORS README LICENSE
%{_mandir}/man1/*.1.gz


%post
# for suse 
if [ -x /usr/lib/lsb/install_initd ]; then
  /usr/lib/lsb/install_initd /etc/init.d/certmaster
# for red hat distros
elif [ -x /sbin/chkconfig ]; then
  /sbin/chkconfig --add certmaster
# or, the old fashioned way
else
   for i in 2 3 4 5; do
        ln -sf /etc/init.d/certmaster /etc/rc.d/rc${i}.d/S99certmaster
   done
   for i in 1 6; do
        ln -sf /etc/init.d/certmaster /etc/rc.d/rc${i}.d/S99certmaster
   done
fi
exit 0

%preun
if [ "$1" = 0 ] ; then
  /etc/init.d/certmaster stop  > /dev/null 2>&1
  if [ -x /usr/lib/lsb/remove_initd ]; then
    /usr/lib/lsb/remove_initd /etc/init.d/certmaster
  elif [ -x /sbin/chkconfig ]; then
    /sbin/chkconfig --del certmaster
  else
    rm -f /etc/rc.d/rc?.d/???certmaster
  fi
fi


%changelog
* Mon Feb 25 2008 Adrian Likins <alikins@redhat.com> - 0.1-1
- remove certmasterd references

* Thu Feb 7 2008 Michael DeHaan <mdehaan@redhat.com> - 0.1-1
- initial version, split off from func project, WIP

