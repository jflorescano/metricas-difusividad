import os
import numpy as np

def procesar_archivos_dti(root_folder):
    stack = [root_folder]  

    while stack:
        current_folder = stack.pop()
        
        for filename in os.listdir(current_folder):
            archivo_completo = os.path.join(current_folder, filename)
            if os.path.isfile(archivo_completo) and filename.endswith("dti.nii.gz") or filename.endswith("dti.nii"):
                basename = os.path.splitext(filename)[0][:-7]
                bvec_filename = os.path.join(current_folder, f"{basename}.bvec")
                bval_filename = os.path.join(current_folder, f"{basename}.bval")
                output_filename = filename.split('_')[0]
                dwi_filename = os.path.join(current_folder, f"dwi_{output_filename}.mif")
                
            
                ################################### Preprocesamiento ############################################
                os.system(f"mrconvert {archivo_completo} {dwi_filename} -fslgrad {bvec_filename} {bval_filename}")
                #denoise
                den_filename = os.path.join(current_folder, f"dwi_den_{output_filename}.mif")
                os.system(f"dwidenoise {dwi_filename} {den_filename}")
                #Eddy current
                preproc_filename = os.path.join(current_folder, f"dwi_den_eddy_{output_filename}.mif")
                os.system(f"dwifslpreproc {den_filename} {preproc_filename} -rpe_none -pe_dir AP -eddy_options \" --slm=linear \"")
                #bias
                bias_filename = os.path.join(current_folder, f"dwi_den_bias_{output_filename}.mif")
                os.system(f"dwibiascorrect ants {preproc_filename} {bias_filename}")
                #mask
                mask_filename = os.path.join(current_folder, f"dwi_den_bias_mask_{output_filename}.mif")
                os.system(f"dwi2mask {bias_filename} {mask_filename}")


                ################################### FODS #######################################################
                #obtener la función de respuesta de los tejidos

                os.system(f"dwi2response dhollander {os.path.join(current_folder, bias_filename)} {os.path.join(current_folder, 'wm.txt')} {os.path.join(current_folder, 'gm.txt')} {os.path.join(current_folder, 'csf.txt')} -fa 0.35 -gm 7 -sfwm 0.9 -csf 8 -voxels {os.path.join(current_folder, 'voxels.mif')}")
                os.system(f"dwi2fod msmt_csd {os.path.join(current_folder, bias_filename)} -mask {os.path.join(current_folder, mask_filename)} {os.path.join(current_folder, 'wm.txt')} {os.path.join(current_folder, 'wmfod.mif')} {os.path.join(current_folder, 'gm.txt')} {os.path.join(current_folder, 'gmfod.mif')} {os.path.join(current_folder, 'csf.txt')} {os.path.join(current_folder, 'csffod.mif')} -lmax 2,0,0")
                os.system(f"mrconvert -coord 3 0 {os.path.join(current_folder, 'wmfod.mif')} - | mrcat {os.path.join(current_folder, 'csffod.mif')} {os.path.join(current_folder, 'gmfod.mif')} - {os.path.join(current_folder, 'vf.mif')}")
                os.system(f"mtnormalise {os.path.join(current_folder, 'wmfod.mif')} {os.path.join(current_folder, 'wmfod_norm.mif')} {os.path.join(current_folder, 'gmfod.mif')} {os.path.join(current_folder, 'gmfod_norm.mif')} {os.path.join(current_folder, 'csffod.mif')} {os.path.join(current_folder, 'csffod_norm.mif')} -mask {os.path.join(current_folder, mask_filename)}")

            
                for filename in os.listdir(current_folder):
                    archivo_completo = os.path.join(current_folder, filename)
                    if os.path.isfile(archivo_completo) and filename.endswith("T1.nii") or filename.endswith("T1.nii.gz"):
                        os.system(f"mrconvert {os.path.join(current_folder, filename)} {os.path.join(current_folder, 'T1.mif')}")
                        os.system(f"5ttgen fsl {os.path.join(current_folder, 'T1.mif')} {os.path.join(current_folder, '5tt_nocoreg.mif')}")
                        #Extraer las imágenes b0
                        os.system(f"dwiextract {os.path.join(current_folder, bias_filename)} - -bzero | mrmath - mean {os.path.join(current_folder, 'mean_b0.mif')} -axis 3")
                        #Conversión a formato nifti
                        os.system(f"mrconvert {os.path.join(current_folder, 'mean_b0.mif')} {os.path.join(current_folder, 'mean_b0.nii.gz')}")
                        os.system(f"mrconvert {os.path.join(current_folder, '5tt_nocoreg.mif')} {os.path.join(current_folder, '5tt_nocoreg.nii.gz')}")
                        #Extraer la segmentación de sustancia gris
                        os.system(f"fslroi {os.path.join(current_folder, '5tt_nocoreg.nii.gz')} {os.path.join(current_folder, '5tt_vol0.nii.gz')} 0 1")
                        #Corregistro de la imagen T1 con la imagen DTI
                        os.system(f"flirt -in {os.path.join(current_folder, 'mean_b0.nii.gz')} -ref {os.path.join(current_folder, '5tt_vol0.nii.gz')} -interp nearestneighbour -dof 6 -omat {os.path.join(current_folder, 'diff2struct_fsl.mat')}")
                        #Conversión de la matriz de corregistro
                        os.system(f"transformconvert {os.path.join(current_folder, 'diff2struct_fsl.mat')} {os.path.join(current_folder, 'mean_b0.nii.gz')} {os.path.join(current_folder, '5tt_nocoreg.nii.gz')} flirt_import {os.path.join(current_folder, 'diff2struct_mrtrix.txt')}")
                        # Command 8: Apply the transformation matrix to the non-coregistered segmentation data
                        os.system(f"mrtransform {os.path.join(current_folder, '5tt_nocoreg.mif')} -linear {os.path.join(current_folder, 'diff2struct_mrtrix.txt')} -inverse {os.path.join(current_folder, '5tt_coreg.mif')}")
                        # Command 10: Create the grey matter / white matter boundary
                        os.system(f"5tt2gmwmi {os.path.join(current_folder, '5tt_coreg.mif')} {os.path.join(current_folder, 'gmwmSeed_coreg.mif')}")

                        
                        ################################# TRACTOGRAFIA ###########################################
                        #Obtener el archivo de los tractos, en este caso se calculan 1 millon 
                        
                        no_tracks = 1000000
                        tracts_filename = os.path.join(current_folder, f"tracks_{no_tracks}.tck")
                        os.system(f"tckgen -act {os.path.join(current_folder, '5tt_coreg.mif')} -backtrack -seed_gmwmi {os.path.join(current_folder, 'gmwmSeed_coreg.mif')} -nthreads 8 -maxlength 250 -cutoff 0.06 -select {no_tracks} {os.path.join(current_folder, 'wmfod_norm.mif')} {tracts_filename}")

                        # Obtener los mapas
                        fa_map_filename = os.path.join(current_folder, "fa_map.mif")
                        adc_map_filename = os.path.join(current_folder, "adc_map.mif")
                        ad_map_filename = os.path.join(current_folder, "ad_map.mif")
                        rd_map_filename = os.path.join(current_folder, "rd_map.mif")
                        os.system(f"dwi2tensor {bias_filename} -mask {mask_filename} - | tensor2metric - -fa {fa_map_filename} -adc {adc_map_filename} -ad {ad_map_filename} -rd {rd_map_filename}")


                        ###################################### METRICAS ################################################

                        # Obtener las métricas en archivos de texto
                        fa_values_filename = os.path.join(current_folder, "fa_values.txt")
                        adc_values_filename = os.path.join(current_folder, "adc_values.txt")
                        ad_values_filename = os.path.join(current_folder, "ad_values.txt")
                        rd_values_filename = os.path.join(current_folder, "rd_values.txt")
                        os.system(f"tcksample {tracts_filename} {fa_map_filename} {fa_values_filename} -stat_tck mean")
                        os.system(f"tcksample {tracts_filename} {adc_map_filename} {adc_values_filename} -stat_tck mean")
                        os.system(f"tcksample {tracts_filename} {ad_map_filename} {ad_values_filename} -stat_tck mean")
                        os.system(f"tcksample {tracts_filename} {rd_map_filename} {rd_values_filename} -stat_tck mean")

                        # Obtener el promedio de todas las métricas
                        # ADC
                        adc_mean = np.mean(np.loadtxt(adc_values_filename))
                        adc_mean_filename = os.path.join(current_folder, "adc_mean.txt")
                        np.savetxt(adc_mean_filename, [adc_mean], fmt='%.18f')
                        # FA
                        fa_mean = np.mean(np.loadtxt(fa_values_filename))
                        fa_mean_filename = os.path.join(current_folder, "fa_mean.txt")
                        np.savetxt(fa_mean_filename, [fa_mean], fmt='%.18f')
                        # AD
                        ad_mean = np.mean(np.loadtxt(ad_values_filename))
                        ad_mean_filename = os.path.join(current_folder, "ad_mean.txt")
                        np.savetxt(ad_mean_filename, [ad_mean], fmt='%.18f')
                        # RD
                        rd_mean = np.mean(np.loadtxt(rd_values_filename))
                        rd_mean_filename = os.path.join(current_folder, "rd_mean.txt")
                        np.savetxt(rd_mean_filename, [rd_mean], fmt='%.18f')

                        # Imprimir valores
                        print(f"DM: {adc_mean}, FA: {fa_mean}, AD: {ad_mean}, RD: {rd_mean}")
                        
                        data = np.array([
                            ['DM:', adc_mean],
                            ['FA:', fa_mean],
                            ['AD:', ad_mean],
                            ['RD:', rd_mean]
                        ])
                        metricas_filename= os.path.join(current_folder, f"metricas_promedios_{output_filename}.txt")
                        np.savetxt(metricas_filename, data, delimiter=' ', fmt='%s')


        subfolders = [os.path.join(current_folder, f) for f in os.listdir(current_folder) if os.path.isdir(os.path.join(current_folder, f))]
        stack.extend(subfolders)
       

      

root_folder = os.getcwd()
procesar_archivos_dti(root_folder)



