/* Private opt-in AWH4 prototype. Include after quakedef.h and aw_harvest.h. */
#ifndef AW_HARVEST_PROXY_H
#define AW_HARVEST_PROXY_H
void AW_HarvestProxyClear(void);
unsigned AW_HarvestProxyBytes(void);
int AW_HarvestProxySpawn(const aw_harvest_t *,aw_state_t *,int,unsigned);
void AW_HarvestProxyLink(void);
entity_t *AW_HarvestProxyEntity(int);
void AW_HarvestProxyHide(int);
#endif
