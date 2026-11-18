# Third-party notices

brgrByte invokes separately developed tools; their licenses remain applicable.
The repository does not vendor the Nmap binary or source. The agent Dockerfile
installs Nmap from Debian at image build time.

`nmap-7.95-LICENSE` is an unmodified copy of the `LICENSE` file from the
[Debian trixie Nmap 7.95+dfsg-3 source package](https://sources.debian.org/src/nmap/7.95%2Bdfsg-3/LICENSE/).
`nmap-7.95+dfsg-3-debian-copyright` is an unmodified copy of the same
package's [Debian copyright and licensing metadata](https://sources.debian.org/src/nmap/7.95%2Bdfsg-3/debian/copyright/),
which identifies additional terms and component licenses. The agent Dockerfile
pins both `nmap` and `nmap-common` to `7.95+dfsg-3` to match these snapshots.
If that version is unavailable from the configured Debian repositories, the
image build fails; update the pin and notices together after review. Native
installations and modified images may use other versions.

Before distributing a release archive or image containing Nmap, determine the
exact version and include its applicable license notices and source availability
information. Review the licenses of all other included components as well.
The agent image includes Debian's package notices under
`/usr/share/doc/<package>/copyright`; verify their presence in the actual image.
Including a license notice does not itself establish that the combination may
be redistributed. Nmap redistribution clearance remains open; see the
[README](../README.md#license-and-third-party-tools).
