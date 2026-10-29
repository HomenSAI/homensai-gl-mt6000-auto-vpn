include $(TOPDIR)/rules.mk

PKG_NAME:=homensai-auto-vpn
PKG_VERSION:=0.9.1-alpha80
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/homensai-auto-vpn
  PKGARCH:=all
  SECTION:=net
  CATEGORY:=Network
  TITLE:=HomenSAI Auto VPN monitor for GL.iNet
  DEPENDS:=+python3 +lua +lua-cjson +libuci-lua +ip-full +ubus +rpcd +luci-base +ca-bundle
endef

define Package/homensai-auto-vpn/description
  Native OpenWrt VPN profile inventory, bound IPv4 HTTPS/DNS monitoring,
  monthly accounting and LuCI interface. Experimental bounded failover with mandatory LAN confirmation.
endef

define Package/homensai-auto-vpn/conffiles
/etc/config/homensai_vpn
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	python3 ./stage_files.py $(PKG_BUILD_DIR)/payload
endef

define Build/Compile
endef

define Package/homensai-auto-vpn/install
	$(CP) $(PKG_BUILD_DIR)/payload/* $(1)/
	chmod 0755 $(1)/etc/init.d/homensai-vpn $(1)/usr/libexec/rpcd/homensai-vpn $(1)/usr/sbin/homensai-vpn-emergency
endef

include ./package-hooks.mk

$(eval $(call BuildPackage,homensai-auto-vpn))
