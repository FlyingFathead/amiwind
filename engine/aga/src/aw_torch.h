/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_TORCH_H
#define AW_TORCH_H
/* Optional emitter data is selected only with a complete appearance pair.
 * Guard lighting and legacy equip availability retain gfx/torch.awt. */
int AW_TorchLoadHandAssets(void);
void AW_TorchUseHandAssets(int enabled);
#endif
