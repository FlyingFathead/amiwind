/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_TORCH_H
#define AW_TORCH_H
#define AW_TORCH_LIGHT_KEY (-0x415754)
#define AW_GUARD_TORCH_LIGHT_KEY (-0x415747)
#define AW_GUARD_TORCH_LIGHT_COUNT 2
extern cvar_t aw_torch_strength;
/* Renderer-relative intensity, separate from the bounded radius. At 0.7,
 * aliases retain their accepted lighting while surfaces gain a peak of
 * 358.4 light units before the existing palette saturation. */
static float AW_TorchLightGain(int key,float radius,int surface)
{
    float strength;
    if(key!=AW_TORCH_LIGHT_KEY &&
       !(key<=AW_GUARD_TORCH_LIGHT_KEY && key>AW_GUARD_TORCH_LIGHT_KEY-AW_GUARD_TORCH_LIGHT_COUNT))return 1;
    strength=aw_torch_strength.value;
    if(!(strength>=0))strength=0;
    if(strength>1)strength=1;
    if(!surface)return strength/.7f;
    if(!(radius>0) || !isfinite(radius))return 0;
    return 512*strength/radius;
}
/* Optional emitter data is selected only with a complete appearance pair.
 * Guard lighting and legacy equip availability retain gfx/torch.awt. */
int AW_TorchLoadHandAssets(void);
void AW_TorchUseHandAssets(int enabled);
void AW_TorchReleaseLegacyCache(void);
#endif
