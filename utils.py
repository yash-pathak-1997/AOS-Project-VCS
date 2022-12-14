import json
import os
import pathlib
import hashlib
import shutil
import pandas as pd
import numpy as np
from Config import UnTrackedDel, UnTrackedMod, UnTrackedNew, TrackedDel, TrackedMod, TrackedNew


def filepath(path, files_list, sha_list, file_track):
    relative = pathlib.Path(os.path.abspath(path))
    for p in pathlib.Path(relative).iterdir():
        if p.is_file():
            files_list.append(str(p).replace("../", ""))
            sha_list.append(hash_calc(p))
            file_track.append(UnTrackedNew)
        elif (p.is_dir()) & (not p.match(".git-vcs")):
            filepath(p, files_list, sha_list, file_track)


def hash_calc(filename):
    sha256_hash = hashlib.sha256()
    f = open(filename, "rb")
    for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_df(files_list, sha_list, track_flag):
    cols_list = ["filename", "sha", "track_flag"]
    df = pd.DataFrame(columns=cols_list)
    df['filename'] = files_list
    df['sha'] = sha_list
    df['track_flag'] = track_flag
    df1 = pd.DataFrame()
    df = pd.concat([df, df1], ignore_index=True)
    return df


def create_log_df(cmd, timestamp, cid, cmsg):
    cols_list = ["ID", "Command", "Timestamp", "CommitId", "CommitMessage"]
    df = pd.DataFrame(columns=cols_list)
    df['Command'] = cmd
    df['Timestamp'] = timestamp
    df['CommitId'] = cid
    df['CommitMessage'] = cmsg
    df1 = pd.DataFrame()
    df = pd.concat([df, df1], ignore_index=True)
    df["ID"] = df.index
    return df


# checking only modify file and delete file and add new file
def update_repo_info(csv_path, repo_path, file_list, sha_list, track_flag):
    new_file_list = list()
    new_sha_list = list()
    new_track_flag = list()
    print(file_list, sha_list, track_flag)
    filepath(repo_path, new_file_list, new_sha_list, new_track_flag)

    # check add new file
    ind = 0
    for i in new_file_list:

        if i not in file_list:
            file_list.append(i)
            sha_list.append(hash_calc(i))
            track_flag.append(UnTrackedNew)

        ind = ind + 1

    # check delete file
    del_list = list()
    for i in range(0, len(file_list)):
        if file_list[i] not in new_file_list:
            if track_flag[i] in [UnTrackedNew, UnTrackedMod, UnTrackedDel]:
                del_list.append(i)

            elif track_flag[i] in [TrackedNew, TrackedMod]:
                file_list.append(file_list[i])
                sha_list.append(None)
                track_flag.append(UnTrackedDel)
    f = 0
    for i in del_list:
        del file_list[i - f]
        del sha_list[i - f]
        del track_flag[i - f]
        f = f + 1

    # check modify file
    for i in range(0, len(file_list)):
        for j in range(0, len(new_file_list)):
            print("enter modify")
            if file_list[i] == new_file_list[j]:
                if sha_list[i] != new_sha_list[j]:
                    if track_flag[i] in [UnTrackedNew, UnTrackedMod, UnTrackedDel]:
                        sha_list[i] = hash_calc(file_list[i])
                        print("..........................")
                        print(file_list[i], track_flag[i])
                        print("..........................")
                    if track_flag[i] in [UnTrackedDel]:
                        track_flag[i] = UnTrackedNew

                    elif track_flag[i] in [TrackedNew, TrackedMod, TrackedDel]:
                        if i != len(file_list) and file_list[i] not in file_list[i + 1:]:
                            file_list.append(file_list[i])
                            sha_list.append(hash_calc(file_list[i]))
                            track_flag.append(UnTrackedMod)
                        else:
                            for k in range(0, len(file_list[i + 1:])):
                                if k + i < len(file_list) and file_list[i] == file_list[k + i]:
                                    # file_list[k]=file_list[i]
                                    sha_list[k] = hash_calc(file_list[i])


# create files and folder when rollback
def create_on_move(df, repo_path, repo_area):
    records = df.to_records(index=False)

    # clear working directory except .git-vcs
    for root, dirs, files in os.walk(repo_path):
        print(root, dirs, files)
        if "git-vcs" not in root:
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                if "git-vcs" not in d:
                    shutil.rmtree(os.path.join(root, d))

    # delete all files which are not tracked from repo_info
    del_list = list()
    for i in range(0, len(records)):
        if "T" not in records[i].track_flag:
            del_list.append(i)

    cntr = 0
    for i in del_list:
        records = np.delete(records, i-cntr)
        cntr += 1

    # create all files and folders in working directory
    for record in records:
        if type(record.sha) != float:
            des = str(record.filename)
            print(des)
            ext = "." + des.split(".")[-1]
            source = str(os.path.join(repo_area, record.sha)) + ext

            if "\\" in record.filename:
                des_path = str(record.filename).replace(("\\" + str(record.filename).split("\\")[-1]), "")
            else:
                des_path = str(record.filename).replace(("/" + str(record.filename).split("/")[-1]), "")
            is_exist = os.path.exists(des_path)
            if not is_exist:
                os.makedirs(des_path)

            shutil.copyfile(source, des)
            record.track_flag = "T0"

    # revert and write back
    final_df = pd.DataFrame(records).iloc[:, 1:]
    return final_df
