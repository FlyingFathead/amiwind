/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_HAND_MODELS_H
#define AW_HAND_MODELS_H
int AW_HandModelsDecode(const unsigned char *data,int size);
void AW_HandModelsLoad(void);
void AW_HandModelsReset(void);
/* Returns one only after selecting a complete, validated appearance. */
int AW_HandModelsApply(void);
#endif
