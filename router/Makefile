include $(TOPDIR)/rules.mk

PKG_NAME:=homensai-auto-vpn
PKG_VERSION:=0.4.0-alpha8
PKG_RELEASE:=1
PKGARCH:=all
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/homensai-auto-vpn
  SECTION:=net
  CATEGORY:=Network
  TITLE:=HomenSAI Auto VPN monitor for GL.iNet
  DEPENDS:=+python3 +lua +lua-cjson +libuci-lua +ip-full +ubus +rpcd +luci-base +ca-bundle
endef

define Package/homensai-auto-vpn/description
  Native OpenWrt VPN profile inventory, bound IPv4 HTTPS/DNS monitoring,
  monthly accounting and LuCI interface. Alpha monitor-only release.
endef

define Package/homensai-auto-vpn/conffiles
/etc/config/homensai_vpn
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
endef

define Build/Compile
endef

define Package/homensai-auto-vpn/install
	$(CP) ./files/* $(1)/
	chmod 0755 $(1)/etc/init.d/homensai-vpn $(1)/usr/libexec/rpcd/homensai-vpn
endef

$(eval $(call BuildPackage,homensai-auto-vpn))
